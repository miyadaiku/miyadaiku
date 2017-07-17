import os
from jinja2 import (TemplateNotFound, Environment, PrefixLoader, FileSystemLoader,
                    ChoiceLoader, PackageLoader, select_autoescape, StrictUndefined)


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


s = '''
{% import "macros.html" as mm %}
{{ str(type(mm)) }}
'''


def create_env(themes, path):
    loaders = [PackagesLoader()]
    if path:
        loaders.append(FileSystemLoader(os.fspath(path)))

    loaders.extend([PackageLoader(theme) for theme in themes])
    loaders.append(PackageLoader('miyadaiku.themes.base'))

    env = Environment(
        undefined=StrictUndefined,
        loader=ChoiceLoader(loaders),
        autoescape=select_autoescape(['html', 'xml'])
    )

    env.globals['repr'] = repr
    env.globals['type'] = type
    env.globals['str'] = str
    env.globals['dir'] = dir

    return env

#
# def render(env, conf, templatename, globals, **kwargs):
#    template = env.get_template(templatename, globals=globals)
#    return template.render(
#        **kwargs
#    )
