import os
from jinja2 import (TemplateNotFound, Environment, PrefixLoader, FileSystemLoader,
                    ChoiceLoader, PackageLoader, select_autoescape, make_logging_undefined,
                    Undefined, DebugUndefined, StrictUndefined)
import logging

logger = logging.getLogger(__name__)


class PackagesLoader(PrefixLoader):
    delimiter = "!"

    def __init__(self):
        self._loaders = {}

    def get_loader(self, template):
        package, *rest = template.split(self.delimiter, 1)
        if not rest:
            raise TemplateNotFound(template)

        if package not in self._loaders:
            self._loaders[package] = PackageLoader(package)

        return self._loaders[package], rest[0]

    def list_templates(self):
        raise TypeError('this loader cannot iterate over all templates')


EXTENSIONS = ['jinja2.ext.do']


def create_env(site, themes, path):
    loaders = [PackagesLoader()]
    if path:
        loaders.append(FileSystemLoader(os.fspath(path)))

    loaders.extend([PackageLoader(theme) for theme in themes])
    loaders.append(PackageLoader('miyadaiku.themes.base'))

    env = Environment(
        undefined=make_logging_undefined(logger, DebugUndefined),
        #        undefined=make_logging_undefined(logger, StrictUndefined),
        loader=ChoiceLoader(loaders),
        autoescape=select_autoescape(['html', 'xml']),
        extensions=EXTENSIONS
    )

    env.globals['site'] = site
    env.globals['repr'] = repr
    env.globals['type'] = type
    env.globals['str'] = str
    env.globals['dir'] = dir
    env.globals['isinstance'] = isinstance
    return env
