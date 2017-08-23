import sys
import pathlib
import importlib
import os
import logging
import shutil
import yaml
import dateutil.parser
import concurrent.futures
import jinja2.exceptions


def timestamp_constructor(loader, node):
    return dateutil.parser.parse(node.value)


yaml.add_constructor(u'tag:yaml.org,2002:timestamp', timestamp_constructor)

import miyadaiku.core
from . import config
from . import contents
from . import jinjaenv
from . import output

logger = logging.getLogger(__name__)
CONFIG_FILE = 'config.yml'
CONTENTS_DIR = 'contents'
FILES_DIR = 'files'
TEMPLATES_DIR = 'templates'
OUTPUTS_DIR = 'outputs'


class Site:
    def __init__(self, path, props=None):
        p = os.path.abspath(os.path.expanduser(path))
        self.path = pathlib.Path(p)
        cfgfile = path / CONFIG_FILE
        self.config = config.Config(cfgfile if cfgfile.exists() else None)

        if props:
            self.config.add('/', props, tail=False)

        self.contents = contents.Contents()

        self.jinjaenv = jinjaenv.create_env(
            self, self.config.themes, path / TEMPLATES_DIR)

        for theme in self.config.themes:
            mod = importlib.import_module(theme)
            f = getattr(mod, 'load_package', None)
            if f:
                f(self)

        contents.load_directory(self, path / CONTENTS_DIR)
        contents.load_directory(self, path / FILES_DIR, contents.bin_loader)

        for theme in self.config.themes:
            contents.load_package(self, theme, CONTENTS_DIR)
            contents.load_package(self, theme, FILES_DIR, contents.bin_loader)

    def add_template_module(self, name, templatename):
        template = self.jinjaenv.get_template(templatename)
        self.jinjaenv.globals[name] = template.module

    def pre_build(self):
        for cont in self.contents.get_contents():
            logger.debug(f'Pre-building {cont.url}')
            cont.pre_build()

    def _build_content(self, key):
        cont = self.contents.get_content(key)
        logger.debug(f'Building {cont.url}')
        outputs = cont.get_outputs()

        output_path = self.path / OUTPUTS_DIR
        for o in outputs:
            o.write(output_path)

    def build(self):
        global _site
        _site = self

        if miyadaiku.core.DEBUG:
            for key in self.contents.get_contents_keys():
                _submit_build(key)
            return

        err = 0

        def done(f):
            exc = f.exception()
            nonlocal err
            if exc:
                err = 1

            if exc and not isinstance(exc, miyadaiku.core.MiyadaikuBuildError):
                print(type(exc), exc)

        if sys.platform == 'win32':
            executer = concurrent.futures.ThreadPoolExecutor
        else:
            executer = concurrent.futures.ProcessPoolExecutor

        with executer() as e:
            for key in self.contents.get_contents_keys():
                f = e.submit(_submit_build, key)
                f.add_done_callback(done)

        return err

    def _get_template(self, basecontent, f, *args, **kwargs):
        try:
            return f(*args, **kwargs)
        except miyadaiku.core.MiyadaikuBuildError:
            raise

        except jinja2.exceptions.TemplateSyntaxError as e:
            src = e.source.split('\n')
            f = max(0, e.lineno - 3)
            lines = []
            for n in range(f, min(f + 5, len(src))):
                if n == (e.lineno - 1):
                    lines.append('>>> ' + src[n])
                else:
                    lines.append('    ' + src[n])

            lines = "\n".join(lines)
            logger.error(
                f'An error occured while compiling {basecontent.url} {type(e)}'
                f'line: {e.lineno} msg: {str(e)}\n'
                f'{lines}'
            )

            exc = miyadaiku.core.MiyadaikuBuildError(str(e))
            exc.filename = basecontent.url
            exc.lineno = e.lineno
            exc.source = e.source

            raise exc

        except Exception as e:
            logger.error(
                f'An error occured while compiling {basecontent.url} {type(e)} msg: {str(e)}')
            exc = miyadaiku.core.MiyadaikuBuildError(str(e))
            exc.filename = basecontent.url
            exc.lineno = None
            raise exc

    def get_template(self, basecontent, name):
        return self._get_template(basecontent, self.jinjaenv.get_template, name)

    def template_from_string(self, basecontent, src):
        return self._get_template(basecontent, self.jinjaenv.from_string, src)

    def render(self, basecontent, template, **kwargs):
        try:
            return template.render(**kwargs)

        except miyadaiku.core.MiyadaikuBuildError:
            raise

        except Exception as e:
            logger.error(
                f'An error occured while rendering {basecontent.url} {type(e)} msg: {str(e)}')
            exc = miyadaiku.core.MiyadaikuBuildError(str(e))
            exc.filename = basecontent.url
            exc.lineno = None
            raise exc


def _submit_build(key):
    try:
        _site._build_content(key)
    except miyadaiku.core.MiyadaikuBuildError:
        raise
    except Exception as e:
        logger.exception(f'Unhandled exception while building {key}')
        raise

# def run():
#     dir = pathlib.Path(sys.argv[1])
#     site = Site(dir)
#     site.build()
#     site.write()


# if __name__ == "__main__":
#     happylogging.initlog(filename='-', level='DEBUG')
#     run()
