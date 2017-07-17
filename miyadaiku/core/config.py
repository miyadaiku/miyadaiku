import collections
import yaml
import pathlib
import locale
import pkg_resources
import tzlocal
import dateutil
import datetime
import fnmatch

from . import utils
from . import YAML_ENCODING
from . import main

default_timezone = tzlocal.get_localzone().zone
default_theme = 'miyadaiku.themes.base'

ignore = [
    '*.exe',
    '*.o',
    '*.so',
    '*.pyc',
    '*.egg-info',
    '*.bak',
    '*.swp',
    '*.~*',
    'dist',
    'build',

    '.DS_Store',
    '._*',
    '.Spotlight-V100',
    '.Trashes',
    'ehthumbs.db',
    'Thumbs.db',
]

defaults = dict(
    ignore=ignore,

    themes=[default_theme, ],
    lang='en',
    charset='utf-8',
    timezone=default_timezone,
    draft=False,
    site_url='http://localhost:8888',
    site_title='(FIXME-site_title)',
    filename_templ='{{page.stem}}{{page.ext}}',
    article_template='page_article.html',

    abstract_length=500,

    use_abs_path=False,

    indexpage_template='page_index.html',
    indexpage_template2='page_index.html',

    indexpage_filename_templ='{{page.stem}}.html',
    indexpage_filename_templ2='{{page.stem}}_{{cur_page}}.html',

    indexpage_group_filename_templ='{{page.stem}}_{{page.groupby}}_{{value}}.html',
    indexpage_group_filename_templ2='{{page.stem}}_{{page.groupby}}_{{value}}_{{cur_page}}.html',

    indexpage_max_num_pages=0,
    indexpage_max_articles=5,
    indexpage_orphan=1,

    feed_type='atom',
    feed_num_articles=10,

    title='',
    date=None,
    category='',
    tags=(),

)


def _load_theme_config(package):
    try:
        s = pkg_resources.resource_string(package, main.CONFIG_FILE)
    except FileNotFoundError:
        cfg = {}
    else:
        cfg = yaml.load(s.decode(YAML_ENCODING))

    if not cfg:
        cfg = {}
    return cfg


def _load_theme_configs(themes):
    seen = set()
    themes = themes[:]
    while themes:
        theme = themes.pop(0)
        if theme in seen:
            continue
        seen.add(theme)
        cfg = _load_theme_config(theme)
        themes = list(t for t in cfg.get('themes', [])) + themes
        yield theme, cfg


class Config:
    def __init__(self, path, props=None):
        self._configs = collections.defaultdict(list)
        self.themes = []

        # read root config
        if path:
            d = yaml.load(path.read_text(encoding=YAML_ENCODING)) or {}
            self.add((), d)

            themes = list(d.get('themes', [])) + [default_theme]
            for theme, cfg in _load_theme_configs(themes):
                self.themes.append(theme)
                self.add((), cfg)

            ignore.extend(list(d.get('ignore', [])))

    def add(self, dirname, cfg, tail=True):
        dirname = utils.dirname_to_tuple(dirname)
        if tail:
            self._configs[dirname].append(cfg)
        else:
            self._configs[dirname].insert(0, cfg)

    _omit = object()

    def get(self, dirname, name, default=_omit):
        if not isinstance(dirname, tuple):
            dirname = utils.dirname_to_tuple(name)

        while True:
            configs = self._configs.get(dirname, None)
            if configs:
                for config in configs:
                    if name in config:
                        return format_value(name, config[name])

            if not dirname:
                if name in defaults:
                    return defaults[name]

                if default is not self._omit:
                    return default
                else:
                    raise AttributeError(
                        f"Invalid config name: {dirname}:{name}")

            dirname = dirname[:-1]

    def getbool(self, dirname, name, default=_omit):
        ret = self.get(dirname, name, default)
        return to_bool(ret)

    def is_ignored(self, name):
        for p in ignore:
            if fnmatch.fnmatch(name, p):
                return True


def load_config(path):
    return Config(yaml.load(path.read_text()))


def to_bool(s):
    if not isinstance(s, str):
        return bool(s)

    s = s.strip().lower()
    # http://yaml.org/type/bool.html
    if s in {'y', 'yes', 'true', 'on'}:
        return True

    if s in {'n', 'no', 'false', 'off'}:
        return False

    raise ValueError(f'Invalid boolean string: {s}')


def format_value(name, value):
    if not isinstance(value, str):
        return value
    value = value.strip()
    if name == 'site_url':
        if value.endswith('/'):
            return value
        return value + '/'
    elif name == 'draft':
        return to_bool(value)
    elif name == 'tags':
        return list(filter(None, (t.strip() for t in value.split(','))))
    elif name == 'date':
        if value:
            ret = dateutil.parser.parse(value)
            if isinstance(ret, datetime.time):
                raise ValueError(f'String does not contain a date: {value!r}')
            return ret
    elif name == 'order':
        return int(value)
    return value
