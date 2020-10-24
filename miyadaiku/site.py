from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Set, Tuple

import dateutil
import importlib_resources
import yaml
from jinja2 import Environment

import miyadaiku

from . import BuildResult, ContentPath, DependsDict, extend, loader
from .builder import Builder, build
from .config import Config
from .jinjaenv import create_env

if TYPE_CHECKING:
    pass


def timestamp_constructor(loader, node):  # type: ignore
    return dateutil.parser.parse(node.value)


yaml.add_constructor("tag:yaml.org,2002:timestamp", timestamp_constructor)  # type: ignore


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

    def __init__(self, rebuild: bool = False, debug: bool = False) -> None:
        self.rebuild = rebuild
        self.debug = debug

    def _load_config(self, props: Dict[str, Any]) -> None:
        cfgfile = self.root / miyadaiku.CONFIG_FILE
        src = ""
        if cfgfile.is_file():
            src = cfgfile.read_text(encoding=miyadaiku.YAML_ENCODING)
        self.siteconfig = (
            yaml.load(
                src,
                Loader=yaml.FullLoader,
            )
            or {}
        )
        self.siteconfig.update(props)

        self.config = Config(self.siteconfig)
        self.stat_config = os.stat(cfgfile) if cfgfile.exists() else None

        self.ignores = set(self.siteconfig.get("ignores", []))

    def _load_themes(self) -> None:
        def _load_theme_config(package: str) -> Dict[str, Any]:
            try:
                path = importlib_resources.files(package)  # type: ignore
                path = path.joinpath(miyadaiku.CONFIG_FILE)
                s = path.read_bytes()
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

    def load_hooks(self) -> None:
        extend.load_hook(self.root)

    def load_modules(self) -> None:
        for theme in self.themes:
            importlib.import_module(theme)

    def _generate_metadata_files(self) -> None:
        for src, content in self.files.items():
            content.generate_metadata_file(self)

    def add_template_module(self, name: str, templatename: str) -> None:
        self.jinja_templates[name] = templatename

    def add_jinja_global(self, name: str, value: Any) -> None:
        self.jinja_global_vars[name] = value

    def load(
        self, root: Path, props: Dict[str, Any], outputdir: Optional[Path] = None
    ) -> None:
        self.root = root.resolve()
        if outputdir:
            self.outputdir = outputdir
        else:
            self.outputdir = self.root / miyadaiku.OUTPUTS_DIR

        self.jinja_global_vars = {}
        self.jinja_templates = {}

        self.load_hooks()
        self._load_config(props)
        self.files = loader.ContentFiles()

        extend.run_initialized(self)

        self._load_themes()

        self._init_themes()

        loader.loadfiles(
            self,
            self.files,
            self.config,
            self.root,
            self.ignores | set(miyadaiku.IGNORE),
            self.themes,
        )

        self._generate_metadata_files()

    def build_jinjaenv(self) -> Environment:
        import miyadaiku.extend

        jinjaenv = create_env(self, self.themes, [self.root / miyadaiku.TEMPLATES_DIR])

        for name, value in miyadaiku.extend.jinja_globals.items():
            jinjaenv.globals[name] = value

        for name, value in self.jinja_global_vars.items():
            jinjaenv.globals[name] = value

        for name, templatename in self.jinja_templates.items():
            template = jinjaenv.get_template(templatename)
            jinjaenv.globals[name] = template.module

        return jinjaenv

    def build(self) -> Tuple[int, int, DependsDict, BuildResult, Set[ContentPath]]:
        return build(self)
