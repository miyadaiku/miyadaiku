import sys
import pathlib
import importlib
import os
import logging
import shutil
import yaml
import collections
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
        try:
            logger.debug(f'Building {cont.url}')
            outputs = cont.get_outputs()

            output_path = self.path / OUTPUTS_DIR


            deps = collections.defaultdict(list)
            for o in outputs:
                created = o.write(output_path)

                src = (o.context.page_content.dirname, o.context.page_content.name)
                relpath = created.relative_to(output_path)
                for ref in o.context.depends:
                    if 'package' in ref.metadata:
                        continue
                    deps[(ref.dirname, ref.name)].append(
                        (str(relpath), src))

            return dict(deps)

        except Exception as e:
            if miyadaiku.core.DEBUG:
                # todo: use logging
                import traceback
                traceback.print_exc()
            exc = _site._translate_exc(cont, e)
            #raise exc
            return {}

    def build(self):
        global _site
        _site = self

        outputs = []
        for key, content in self.contents.items():
            outputs.extend(content.get_outputs())

        output_path = self.path / OUTPUTS_DIR
        deps = collections.defaultdict(set)
        for output in outputs:
            ret = output.build(output_path)

        return 0, {}

#
#            for key in self.contents.get_contents_keys():
#                ret = _submit_build(key)
#                for k, v in ret.items():
#                    deps[k].extend(v)
#
#            return 0, deps
#
#        err = 0
#
#
#        def done(f):
#            exc = f.exception()
#            nonlocal err
#            if exc:
#                err = 1
#
#            if exc and not isinstance(exc, miyadaiku.core.MiyadaikuBuildError):
#                return
#
#            ret = f.result()
#            for k, v in ret.items():
#                deps[k].extend(v)
#
#        if sys.platform == 'win32':
#            executer = concurrent.futures.ThreadPoolExecutor
#        else:
#            executer = concurrent.futures.ProcessPoolExecutor
#
#        with executer() as e:
#            for key in self.contents.get_contents_keys():
#                f = e.submit(_submit_build, key)
#                f.add_done_callback(done)

        return err, deps

    def _translate_exc(self, content, e):
        if isinstance(e, jinja2.exceptions.TemplateSyntaxError):
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
                f'An error occured while compiling {content} {type(e)}'
                f'line: {e.lineno} msg: {str(e)}\n'
                f'{lines}'
            )

            exc = miyadaiku.core.MiyadaikuBuildError(str(e))
            exc.filename = content.url
            exc.lineno = e.lineno
            exc.source = e.source

            return exc

        else:
            logger.error(
                f'An error occured while compiling {content.url} {type(e)} msg: {str(e)}')
            exc = miyadaiku.core.MiyadaikuBuildError(str(e))
            exc.filename = content.url
            exc.lineno = None
            return exc

    def _get_template(self, basecontent, f, *args, **kwargs):
        try:
            return f(*args, **kwargs)
        except miyadaiku.core.MiyadaikuBuildError:
            raise

        except Exception as e:
            exc = self._translate_exc(basecontent, e)
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
    return _site._build_content(key)

# def run():
#     dir = pathlib.Path(sys.argv[1])
#     site = Site(dir)
#     site.build()
#     site.write()


# if __name__ == "__main__":
#     happylogging.initlog(filename='-', level='DEBUG')
#     run()
