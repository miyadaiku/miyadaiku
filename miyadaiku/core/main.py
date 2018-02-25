import sys
import pickle
import pathlib
import importlib
import hashlib
import os
import io
import logging
import enum
import shutil
import yaml
import traceback
import collections
import dateutil.parser
import concurrent.futures
import jinja2.exceptions


class _MiyadaukuJunja2SyntaxError(Exception):
    source = ''
    lineno = 1
    filename = None


def timestamp_constructor(loader, node):
    return dateutil.parser.parse(node.value)


yaml.add_constructor(u'tag:yaml.org,2002:timestamp', timestamp_constructor)

import miyadaiku.core
from . import config
from . import contents
from . import jinjaenv
from . exception import MiyadaikuBuildError
from .hooks import run_hook, HOOKS

logger = logging.getLogger(__name__)
CONFIG_FILE = 'config.yml'
CONTENTS_DIR = 'contents'
FILES_DIR = 'files'
TEMPLATES_DIR = 'templates'
OUTPUTS_DIR = 'outputs'
DEP_FILE = '_depends.pickle'
DEP_VER = '1.0.2'


class Site:
    rebuild = False
    depends = frozenset()
    stat_depfile = None

    def __init__(self, path, props=None, show_traceback=None, debug=None):
        self.debug = debug
        if self.debug is None:
            self.debug = miyadaiku.core.DEBUG

        self.show_traceback = show_traceback
        if self.show_traceback is None:
            self.show_traceback = miyadaiku.core.SHOW_TRACEBACK or self.debug

        p = os.path.abspath(os.path.expanduser(path))
        self.path = pathlib.Path(p)
        cfgfile = path / CONFIG_FILE
        self.config = config.Config(cfgfile if cfgfile.exists() else None, props)
        self.stat_config = os.stat(cfgfile) if cfgfile.exists() else None

        self.contents = contents.Contents()

        self.jinjaenv = jinjaenv.create_env(
            self, self.config.themes, path / TEMPLATES_DIR)

        for theme in self.config.themes:
            mod = importlib.import_module(theme)
            f = getattr(mod, 'load_package', None)
            if f:
                f(self)

        run_hook(HOOKS.initialized, self)

        contents.load_directory(self, path / CONTENTS_DIR)
        contents.load_directory(self, path / FILES_DIR, contents.bin_loader)

        for theme in self.config.themes:
            contents.load_package(self, theme, CONTENTS_DIR)
            contents.load_package(self, theme, FILES_DIR, contents.bin_loader)

        self._init_jinja_globals()
        run_hook(HOOKS.loaded, self)

    def _init_jinja_globals(self):
        import miyadaiku.extend
        for name, value in miyadaiku.extend._jinja_globals.items():
            self.add_jinja_global(name, value)

    def add_template_module(self, name, templatename):
        template = self.jinjaenv.get_template(templatename)
        self.jinjaenv.globals[name] = template.module

    def add_jinja_global(self, name, f):
        self.jinjaenv.globals[name] = f

    def nthlines(self, filename, src, lineno):
        if src is None:
            try:
                if filename and os.path.exists(filename):
                    src = open(filename).read()
            except IOError:
                src = ''

        if not src:
            return ''
        src = src.split('\n')
        f = max(0, lineno - 3)
        lines = []
        for n in range(f, min(f + 5, len(src))):
            if n == (lineno - 1):
                lines.append('  >>> ' + src[n])
            else:
                lines.append('      ' + src[n])

        lines = "\n".join(lines).rstrip() + '\n'
        return lines

    def _exc_to_dict(self, content, e):
        t = io.StringIO()
        traceback.print_exception(type(e), e, e.__traceback__, file=t)
        tb = t.getvalue()

        if not isinstance(e, MiyadaikuBuildError):
            e = MiyadaikuBuildError(e, content, None, None)
        ret = e.to_dict()
        ret['tb'] = tb
        return ret

    def _print_err_dict(self, d):
        logger.error(f'Error in {d["srcfilename"]} while building {d["pagefilename"]}')
        logger.error(f'  {d["exctype"]}: {d["args"][0].rstrip()}')

        if self.show_traceback:
            logger.error(d['tb'])

    def pre_build(self):
        for cont in self.contents.get_contents():
            try:
                logger.debug(f'Pre-building {cont.srcfilename}')
                cont.pre_build()
            except Exception as e:
                d = self._exc_to_dict(cont, e)
                self._print_err_dict(d)
                raise e

    def get_metadatas(self):
        all = {}
        for k, c in self.contents.items():
            m = dict(c.metadata)
            if 'stat' in m:
                del m['stat']
            all[k] = m

        return all

    def save_deps(self):
        keys = set(self.contents.get_contents_keys())
        metadatas = self.get_metadatas()
        o = (DEP_VER, keys, (self.rebuild_always, self.depends, metadatas))

        try:
            with open(self.path / DEP_FILE, "wb") as f:
                pickle.dump(o, f)
        except IOError as e:
            logger.warn(f'Falied to write {self.path / DEP_FILE}: {e}')

    def load_deps(self):
        self.depends = collections.defaultdict(set)
        self.rebuild_always = set()

        deppath = self.path / DEP_FILE
        try:
            with open(deppath, "rb") as f:
                ver, keys, values = pickle.load(f)
            if ver != DEP_VER:
                self.rebuild = True
                return
            rebuild_always, deps, metadatas = values
        except Exception:
            self.rebuild = True
            return

        if metadatas != self.get_metadatas():
            self.rebuild = True
            return

        self.stat_depfile = os.stat(deppath)

        if self.stat_config and self.stat_config.st_mtime > self.stat_depfile.st_mtime:
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
            if (key in rebuild_always) or content.check_update(output_path):
                content.updated = True

                if isinstance(content, contents.ConfigContent):
                    self.rebuild = True
                    return

        updated_items = [content for key, content in self.contents.items() if content.updated]

        while updated_items:
            updated = []
            for content in updated_items:
                refs = deps.get((content.dirname, content.name), ())
                for filename, ref, pagearg in refs:
                    if self.contents.has_content(ref):
                        c = self.contents.get_content(ref)
                        if not c.updated:
                            c.updated = True
                            updated.append(c)

            updated_items = updated

        self.depends = deps
        self.rebuild_always = rebuild_always

    def _run_build(self, content):
        logger.info(f'Building {content.srcfilename}')

        output_path = self.path / OUTPUTS_DIR
        run_hook(HOOKS.pre_build, self, content, output_path)
        try:
            destfiles, context = content.build(output_path)
        except Exception as e:
            d = self._exc_to_dict(content, e)
            return None, False, d

        run_hook(HOOKS.post_build, self, content, output_path, destfiles)

        src = (content.dirname, content.name)

        deps = collections.defaultdict(set)
        refs, pageargs = context.get_depends()
        for ref in refs:
            if 'package' in ref.metadata:
                continue
            deps[(ref.dirname, ref.name)].update(
                (dest, src, pageargs) for dest in destfiles)

        return deps, context.is_rebuild_always(), None

    def build(self):
        global _site
        _site = self

        self.load_deps()

        if self.debug:
            for key, content in self.contents.items():
                if not self.rebuild and not content.updated:
                    continue
                ret, rebuild_always, d = self._run_build(content)
                if ret is None:
                    self._print_err_dict(d)
                    return 1, {}

                for k, v in ret.items():
                    self.depends[k].update(v)

                if rebuild_always:
                    self.rebuild_always.add((content.dirname, content.name))

            self.save_deps()
            return 0

        if sys.platform == 'win32':
            executer = concurrent.futures.ThreadPoolExecutor
        else:
            executer = concurrent.futures.ProcessPoolExecutor

        errs = []

        def done(f, key):
            content = self.contents.get_content(key)
            try:
                ret, rebuild_always, d = f.result()
            except Exception as e:
                d = self._exc_to_dict(content, e)
                errs.append(d)
                raise e

            if ret is None:
                errs.append(d)
                return

            for k, v in ret.items():
                self.depends[k].update(v)

            if rebuild_always:
                self.rebuild_always.add((content.dirname, content.name))

        with executer() as e:
            for key, content in self.contents.items():
                if not self.rebuild and not content.updated:
                    continue
                f = e.submit(_run, key)
                f.add_done_callback(lambda f, key=key: done(f, key))

        if not errs:
            self.save_deps()

        for err in errs:
            self._print_err_dict(err)

        return 1 if errs else 0


def _run(key):
    content = _site.contents.get_content(key)
    return _site._run_build(content)
