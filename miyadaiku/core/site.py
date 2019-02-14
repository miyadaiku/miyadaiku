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

def timestamp_constructor(loader, node):
    return dateutil.parser.parse(node.value)

yaml.add_constructor(u'tag:yaml.org,2002:timestamp', timestamp_constructor)

import miyadaiku.core
from . import config
from . import contents
from . import jinjaenv
from . import builder
from . exception import MiyadaikuBuildError
from .hooks import run_hook, HOOKS
from . utils import import_script

logger = logging.getLogger(__name__)
CONFIG_FILE = 'config.yml'
MODULES_DIR = 'modules'
CONTENTS_DIR = 'contents'
FILES_DIR = 'files'
TEMPLATES_DIR = 'templates'
OUTPUTS_DIR = 'outputs'


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

        modules = (path / MODULES_DIR).resolve()
        if modules.is_dir():
            s = str(modules)
            if s not in sys.path:
                sys.path.insert(0, s)

            for f in modules.iterdir():
                if not f.is_file():
                    continue
                if f.suffix != '.py':
                    continue
                name = f.stem
                if not name.isidentifier():
                    continue
                m = import_script(name, f)

                self.add_jinja_global(name, m)


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

    def pre_build(self):
        for cont in self.contents.get_contents():
            logger.debug(f'Pre-building {cont.srcfilename}')
            cont.pre_build()

    def build(self):
        self.pre_build()
        builder.build(self)
