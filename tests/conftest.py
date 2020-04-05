# type: ignore

import pytest
import pathlib
import logging
from typing import Any, Dict
import yaml

import miyadaiku.site

logging.getLogger().setLevel(logging.DEBUG)

# import miyadaiku

# miyadaiku.core.SHOW_TRACEBACK = True
# miyadaiku.core.DEBUG = True


@pytest.fixture
def sitedir(tmpdir: Any) -> pathlib.Path:
    d = tmpdir.mkdir("site")
    d.mkdir("modules")
    d.mkdir("contents")
    d.mkdir("files")
    d.mkdir("templates")
    return pathlib.Path(str(d))


class SiteRoot:
    path: pathlib.Path
    contents: pathlib.Path
    files: pathlib.Path
    templates: pathlib.Path
    modules: pathlib.Path

    def __init__(self, path: str) -> None:
        self.path = pathlib.Path(str(path)) / "site"
        self.path.mkdir()

        self.contents = self.path / "contents"
        self.files = self.path / "files"
        self.templates = self.path / "templates"
        self.modules = self.path / "modules"

    def load(
        self, config: Dict[Any, Any], props: Dict[Any, Any]
    ) -> miyadaiku.site.Site:
        cfg = yaml.dump(config)
        (self.path / "config.yml").write_text(cfg)

        site = miyadaiku.site.Site()
        site.load(self.path, props)
        return site

    def ensure_parent(self, path: pathlib.Path) -> None:
        parent = path.parent
        if not parent.is_dir():
            parent.mkdir(parents=True, exist_ok=True)

    def write_text(self, path: pathlib.Path, text: str) -> pathlib.Path:
        self.ensure_parent(path)
        path.write_text(text)
        return path

    def write_bytes(self, path: pathlib.Path, bin: bytes) -> pathlib.Path:
        self.ensure_parent(path)
        path.write_bytes(bin)
        return path


@pytest.fixture
def siteroot(tmpdir: Any) -> SiteRoot:
    ret = SiteRoot(tmpdir)
    return ret
