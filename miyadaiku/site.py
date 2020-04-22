from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Set, Tuple, Sequence
import sys
import os
from pathlib import Path
import importlib
import importlib.util
import importlib.abc
import yaml
import pkg_resources
import dateutil

from jinja2 import Environment

import miyadaiku
from .config import Config
from . import ContentSrc, ContentPath, loader
from .builder import create_builders, Builder, build
from .jinjaenv import create_env

if TYPE_CHECKING:
    from .context import OutputContext


def timestamp_constructor(loader, node):  # type: ignore
    return dateutil.parser.parse(node.value)


yaml.add_constructor(u"tag:yaml.org,2002:timestamp", timestamp_constructor)  # type: ignore


def _import_script(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)

    assert isinstance(spec.loader, importlib.abc.Loader)
    spec.loader.exec_module(m)
    sys.modules[name] = m
    return m


class Site:
    root: Path
    sitecondig: Dict[str, Any]
    config: Config
    files: loader.ContentFiles
    ignores: Set[str]
    themes: List[str]
    builders: List[Builder]

    jinja_global_vars: Dict[str, Any]
    jinja_templates: Dict[str, Any]
    jinjaenv: Environment

    def _load_config(self, props: Dict[str, Any]) -> None:
        cfgfile = self.root / miyadaiku.CONFIG_FILE
        src = ""
        if cfgfile.is_file():
            src = cfgfile.read_text(encoding=miyadaiku.YAML_ENCODING)
        self.siteconfig = yaml.load(src, Loader=yaml.FullLoader,) or {}
        self.siteconfig.update(props)

        self.config = Config(self.siteconfig)
        self.stat_config = os.stat(cfgfile) if cfgfile.exists() else None

        self.ignores = set(self.siteconfig.get("ignores", []))

    def _load_themes(self) -> None:
        def _load_theme_config(package: str) -> Dict[str, Any]:
            try:
                s = pkg_resources.resource_string(package, miyadaiku.CONFIG_FILE)
            except FileNotFoundError:
                cfg = {}
            else:
                cfg = yaml.load(
                    s.decode(miyadaiku.YAML_ENCODING), Loader=yaml.FullLoader
                )

            if not cfg:
                cfg = {}
            return cfg

        def _load_theme_configs(
            themes: List[str],
        ) -> Iterator[Tuple[str, Dict[str, Any]]]:
            seen = set()
            themes = themes[:]
            while themes:
                theme = themes.pop(0).strip()
                if theme in seen:
                    continue
                seen.add(theme)

                cfg = _load_theme_config(theme)
                themes = list(t for t in cfg.get("themes", [])) + themes
                yield theme, cfg

        themes = self.siteconfig.get("themes", [])
        themes.append(miyadaiku.DEFAULT_THEME)

        self.themes = []
        for theme, cfg in _load_theme_configs(themes):
            self.themes.append(theme)
            self.config.add_themecfg(cfg)

    def _init_themes(self) -> None:
        for theme in self.themes:
            mod = importlib.import_module(theme)
            f = getattr(mod, "load_package", None)
            if f:
                f(self)

    def load_modules(self) -> None:
        modules = (self.root / miyadaiku.MODULES_DIR).resolve()
        if modules.is_dir():
            s = str(modules)
            if s not in sys.path:
                sys.path.insert(0, s)

            for f in modules.iterdir():
                if not f.is_file():
                    continue
                if f.suffix != ".py":
                    continue
                name = f.stem
                if not name.isidentifier():
                    continue
                m = _import_script(name, f)

                self.add_jinja_global(name, m)

    def _generate_metadata_files(self) -> None:
        for src, content in self.files.items():
            content.generate_metadata_file(self)

    def add_template_module(self, name: str, templatename: str) -> None:
        self.jinja_templates[name] = templatename

    def add_jinja_global(self, name: str, value: Any) -> None:
        self.jinja_global_vars[name] = value

    def load(self, root: Path, props: Dict[str, Any]) -> None:
        self.root = root
        self.outputdir = self.root / miyadaiku.OUTPUTS_DIR

        self.jinja_global_vars = {}
        self.jinja_templates = {}

        self._load_config(props)
        self.files = loader.ContentFiles()

        self._load_themes()

        self._init_themes()

        loader.loadfiles(self.files, self.config, self.root, self.ignores, self.themes)

        self._generate_metadata_files()

    def build_jinjaenv(self) -> Environment:
        jinjaenv = create_env(
            self, self.themes, [self.root / miyadaiku.TEMPLATES_DIR]
        )

        for name, value in self.jinja_global_vars.items():
            jinjaenv.globals[name] = value

        for name, templatename in self.jinja_templates.items():
            template = jinjaenv.get_template(templatename)
            jinjaenv.globals[name] = template.module

        return jinjaenv

    def build(self) -> Sequence[Tuple[ContentSrc, Set[ContentPath]]]:
        return build(self)
