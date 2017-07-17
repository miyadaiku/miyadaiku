import sys
import pathlib
import importlib
import os
import logging
import shutil

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
        self.output = output.Outputs()

        self.jinjaenv = jinjaenv.create_env(
            self.config.themes, path / TEMPLATES_DIR)

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

    def build(self):
        for cont in self.contents.get_contents():
            logger.info(f'Building {cont.url}')
            outputs = cont.get_outputs()

            for o in outputs:
                self.output.add(o)

    def write(self):
        try:
            shutil.rmtree(self.path / OUTPUTS_DIR)
        except FileNotFoundError:
            pass

        self.output.write(self.path / OUTPUTS_DIR)

    def render(self, template, **kwargs):
        return template.render(**kwargs)


# def run():
#     dir = pathlib.Path(sys.argv[1])
#     site = Site(dir)
#     site.build()
#     site.write()


# if __name__ == "__main__":
#     happylogging.initlog(filename='-', level='DEBUG')
#     run()
