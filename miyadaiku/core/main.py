import sys
import pickle
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
DEP_FILE = '_depends.pickle'
DEP_VER = '1.0.0'


class Site:
    rebuild = False
    depends = frozenset()
    stat_depfile = None

    def __init__(self, path, props=None):
        p = os.path.abspath(os.path.expanduser(path))
        self.path = pathlib.Path(p)
        cfgfile = path / CONFIG_FILE
        self.config = config.Config(cfgfile if cfgfile.exists() else None)
        self.stat_config = os.stat(cfgfile) if cfgfile.exists() else None

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

    def save_deps(self, deps):
        keys = set(self.contents.get_contents_keys())
        o = (DEP_VER, keys, deps)
        try:
            with open(self.path / DEP_FILE, "wb") as f:
                pickle.dump(o, f)
        except IOError as e:
            logger.warn(f'Falied to write {self.path / DEP_FILE}: {e}')

    def load_deps(self):
        deppath = self.path / DEP_FILE
        try:
            with open(deppath, "rb") as f:
                DEP_VER, keys, deps = pickle.load(f)
        except IOError:
            self.rebuild = True
            return

        self.stat_depfile = os.stat(deppath)
        if self.stat_config.st_mtime > self.stat_depfile.st_mtime:
            self.rebuild = True
            return

        for root, dirs, files in os.walk(self.path / TEMPLATES_DIR):
            root = pathlib.Path(root)
            for file in files:
                if (root / file).stat().st_mtime > self.stat_depfile.st_mtime:
                    self.rebuild = True
                    return

        curkeys = set(self.contents.get_contents_keys())
        created = curkeys - keys
        deleted = keys - curkeys

        if deleted or created:
            self.rebuild = True
            return

        output_path = self.path / OUTPUTS_DIR
        for key, content in self.contents.items():
            if content.check_update(output_path):
                refs = deps.get((content.dirname, content.name), ())
                for filename, ref, pagearg in refs:
                    if self.contents.has_content(ref):
                        c = self.contents.get_content(ref)
                        c.updated = True

                if isinstance(content, contents.ConfigContent):
                    self.rebuild = True
                    return

        self.depends = deps

    def _run_build(self, output):
        logger.debug(f'Building {output.content.url}')
        output_path = self.path / OUTPUTS_DIR
        try:
            dest, context = output.build(output_path)
        except Exception as e:
            if miyadaiku.core.DEBUG:
                # todo: use logging
                import traceback
                traceback.print_exc()
            exc = _site._translate_exc(output.content, e)
            #raise exc
            return None

        src = (output.content.dirname, output.content.name)

        deps = collections.defaultdict(set)
        refs, pageargs = context.get_depends()
        for ref in refs:
            if 'package' in ref.metadata:
                continue
            deps[(ref.dirname, ref.name)].add(
                (dest, src, pageargs))

        return deps

    def build(self):
        global _site
        _site = self

        self.load_deps()

        self.outputs = []
        for key, content in self.contents.items():
            self.outputs.extend(content.get_outputs())

        output_path = self.path / OUTPUTS_DIR
        deps = collections.defaultdict(set)

        if miyadaiku.core.DEBUG:
            for output in self.outputs:
                if not output.content.updated:
                    continue

                ret = self._run_build(output)
                if ret is None:
                    return 1, {}

                for k, v in ret.items():
                    deps[k].update(v)

                self.save_deps(deps)

            return 0

        if sys.platform == 'win32':
            executer = concurrent.futures.ThreadPoolExecutor
        else:
            executer = concurrent.futures.ProcessPoolExecutor

        err = 0

        def done(f):
            nonlocal err
            try:
                ret = f.result()
            except Exception as e:
                err = 1
                raise e

            if ret is None:
                err = 1
                return

            for k, v in ret.items():
                deps[k].update(v)

        with executer() as e:
            for i in range(len(self.outputs)):
                if not self.rebuild and not self.outputs[i].content.updated:
                    continue
                f = e.submit(_run, i)
                f.add_done_callback(done)

        self.save_deps(deps)
        return err

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
                f'An error occured while compiling {content} {type(e)}\n'
                f'{e.filename}:{e.lineno} {str(e)}\n'
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


def _run(n):
    output = _site.outputs[n]
    return _site._run_build(output)


# def run():
#     dir = pathlib.Path(sys.argv[1])
#     site = Site(dir)
#     site.build()
#     site.write()


# if __name__ == "__main__":
#     happylogging.initlog(filename='-', level='DEBUG')
#     run()
