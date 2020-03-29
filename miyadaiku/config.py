from typing import List, Dict, Optional, DefaultDict, Any, Callable
import os
import collections
import dateutil.parser
import datetime

import miyadaiku
from miyadaiku import ContentSrc, PathTuple


DEFAULTS = dict(
    ignore=[],
    themes=[miyadaiku.DEFAULT_THEME],
    lang="en-US",
    charset="utf-8",
    timezone=miyadaiku.DEFAULT_TIMEZONE,
    draft=False,
    site_url="http://localhost:8888",
    site_title="(FIXME-site_title)",
    filename_templ="{{content.stem}}{{content.ext}}",
    article_template="page_article.html",
    abstract_length=500,
    use_abs_path=False,
    indexpage_template="page_index.html",
    indexpage_template2="page_index.html",
    indexpage_filename_templ="{{content.stem}}.html",
    indexpage_filename_templ2="{{content.stem}}_{{cur_page}}.html",
    indexpage_group_filename_templ=(
        "{{content.stem}}_{{content.groupby}}_{{value}}.html"
    ),
    indexpage_group_filename_templ2=(
        "{{content.stem}}_{{content.groupby}}_{{value}}_{{cur_page}}.html"
    ),
    indexpage_max_num_pages=0,
    indexpage_max_articles=5,
    indexpage_orphan=1,
    feed_type="atom",
    feed_num_articles=10,
    title="",
    date=None,
    category="",
    tags=(),
    order=0,
    og_type="article",
    og_title="",
    og_image="",
    og_description="",
    ga_tracking_id="",
    imports="",
    generate_metadata_file=False,
)


THEME_CONF_ENTRIES = ["themes"]


def remove_theme_confs(cfg: Dict[str, Any]) -> Dict[str, Any]:
    ret = {}
    for k, v in cfg.items():
        if k not in THEME_CONF_ENTRIES:
            ret[k] = v
    return ret


class Config:
    updated: float
    _configs: DefaultDict[PathTuple, List[Dict[str, Any]]]

    def __init__(self, d: Dict[str, Any]):
        self._configs = collections.defaultdict(list)
        self.updated = 0
        self.root = d
        self.themes: List[Dict[str, Any]] = []

    def add_themecfg(self, cfg: Dict[str, Any]) -> None:
        self.themes.append(cfg)

    def add(
        self,
        dirname: PathTuple,
        cfg: Dict[str, Any],
        contentsrc: Optional[ContentSrc] = None,
        tail: bool = True,
    ) -> None:
        cfg = cfg.copy()
        if "type" in cfg:
            del cfg["type"]

        if not cfg:
            return

        if tail:
            self._configs[dirname].append(cfg)
        else:
            self._configs[dirname].insert(0, cfg)

        if contentsrc:
            if not contentsrc.package:
                mtime = os.stat(contentsrc.srcpath).st_mtime
                self.updated = max(self.updated, mtime)

    _omit = object()

    def get(self, dirname: PathTuple, name: str, default: Any = _omit) -> Any:
        while True:
            configs = self._configs.get(dirname, None)
            if configs:
                for config in configs:
                    if name in config:
                        return format_value(name, config[name])

            if not dirname:
                if name in self.root:
                    return format_value(name, self.root[name])

                for config in self.themes:
                    if name in config:
                        return format_value(name, config[name])

                if name in DEFAULTS:
                    return DEFAULTS[name]

                if default is not self._omit:
                    return default

                raise AttributeError(f"Invalid config name: {dirname}:{name}")

            dirname = dirname[:-1]

    def getbool(self, dirname: PathTuple, name: str, default: Any = _omit) -> bool:
        ret = self.get(dirname, name, default)
        return to_bool(ret)


#    def is_ignored(self, name):
#        for p in IGNORE:
#            if fnmatch.fnmatch(name, p):
#                return True


def to_bool(s: Any) -> bool:
    if not isinstance(s, str):
        return bool(s)

    s = s.strip().lower()
    # http://yaml.org/type/bool.html
    if s in {"y", "yes", "true", "on"}:
        return True

    if s in {"n", "no", "false", "off"}:
        return False

    raise ValueError(f"Invalid boolean string: {s}")


VALUE_CONVERTERS: Dict[str, Callable[[Any], Any]] = {}


def value_converter(f: Any) -> Any:
    VALUE_CONVERTERS[f.__name__] = f
    return f


@value_converter
def site_url(value: Any) -> Any:
    if value.endswith("/"):
        return value
    return value + "/"


@value_converter
def draft(value: Any) -> Any:
    return to_bool(value)


@value_converter
def tags(value: Any) -> Any:
    if isinstance(value, str):
        return list(filter(None, (t.strip() for t in value.split(","))))
    return value


@value_converter
def date(value: str) -> Any:
    if value:
        ret = dateutil.parser.parse(value)
        if isinstance(ret, datetime.time):
            raise ValueError(f"string does not contain a date: {value!r}")
        return ret


@value_converter
def order(value: Any) -> Any:
    return int(value)


@value_converter
def imports(value: Optional[str]) -> Any:
    if value:
        return [s.strip() for s in value.split(",")]
    else:
        return []


def format_value(name: str, value: Any) -> Any:
    f = VALUE_CONVERTERS.get(name)
    if f:
        return f(value)

    return value


# def load(path: Optional[Path]) -> Config:
#    if path:
#        d: dict = yaml.load(
#            path.read_text(encoding=miyadaiku.YAML_ENCODING), Loader=yaml.FullLoader
#        ) or {}
#    else:
#        d = {}
#    return Config(d)
#
#
# def _load_theme_config(package: str) -> Dict:
#    try:
#        s = pkg_resources.resource_string(package, miyadaiku.CONFIG_FILE)
#    except FileNotFoundError:
#        cfg = {}
#    else:
#        cfg = yaml.load(s.decode(miyadaiku.YAML_ENCODING), Loader=yaml.FullLoader)
#
#    if not cfg:
#        cfg = {}
#    return cfg
#
#
# def _load_theme_configs(themes: List[str]) -> Iterator[Tuple[str, Dict]]:
#    seen = set()
#    themes = themes[:]
#    while themes:
#        theme = themes.pop(0)
#        if theme in seen:
#            continue
#        seen.add(theme)
#
#        cfg = _load_theme_config(theme)
#        themes = list(t for t in cfg.get("themes", [])) + themes
#        yield theme, cfg
#
#
# def load_themes(config: Config):
#    themenames = list(config.get((), "themes"))
#    if not themenames:
#        themenames = [miyadaiku.DEFAULT_THEME]
#
#    themes = []
#    for theme, cfg in _load_theme_configs(themenames):
#        themes.append(theme)
#        config.add((), cfg)
#
#    return themes
