from __future__ import annotations

import copy
import datetime
import posixpath
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Set, Tuple, Union

import importlib_resources
import tzlocal

__version__ = "1.26.0"

YAML_ENCODING = "utf-8"


CONFIG_FILE = "config.yml"
MODULES_DIR = "modules"
CONTENTS_DIR = "contents"
FILES_DIR = "files"
TEMPLATES_DIR = "templates"
NBCONVERT_TEMPLATES_DIR = "nb_templates"
OUTPUTS_DIR = "outputs"
SITEMAP_FILENAME = "sitemap.xml"
SITEMAP_CHANGEFREQ = "daily"

zinfo = tzlocal.get_localzone()
try:
    DEFAULT_TIMEZONE = zinfo.zone
except AttributeError:
    DEFAULT_TIMEZONE = str(zinfo)

DEFAULT_THEME = "miyadaiku.themes.base"

IGNORE = [
    ".*",
    "*.o",
    "*.pyc",
    "*.egg-info",
    "*.bak",
    "*.swp",
    "*.~*",
    "dist",
    "build",
    "ehthumbs.db",
    "Thumbs.db",
    ".ipynb_checkpoints",
]

METADATA_FILE_SUFFIX = ".props.yml"

PathTuple = Tuple[str, ...]
ContentPath = Tuple[PathTuple, str]


class ContentSrc(NamedTuple):
    package: Optional[str]
    srcpath: Optional[str]
    metadata: Dict[str, Any]
    contentpath: ContentPath
    mtime: Optional[float] = 0.0

    def copy(self) -> ContentSrc:
        return copy.deepcopy(self)

    def repr_filename(self) -> str:
        if self.srcpath:
            if self.package:
                return f"{self.package}!{self.srcpath}"
            else:
                return f"{self.srcpath}"
        else:
            if self.package:
                return f"{self.package}!{repr_contentpath(self.contentpath)}"
            else:
                return f"{repr_contentpath(self.contentpath)}"

    def is_package(self) -> bool:
        return bool(self.package)

    def get_package_path(self) -> Any:
        if self.package and self.srcpath:
            path = importlib_resources.files(self.package)
            return path.joinpath(self.srcpath)
        return None

    def stat(self) -> Any:
        path = self.get_package_path()
        if path:
            return path.stat()
        else:
            assert self.srcpath
            return Path(self.srcpath).stat()

    def read_text(self, encoding: str = "utf-8") -> str:
        path = self.get_package_path()
        if path:
            text: str = path.read_text()
            return text
        else:
            assert self.srcpath
            return open(self.srcpath).read()

    def read_bytes(self) -> bytes:
        path = self.get_package_path()
        if path:
            ret: bytes = path.read_bytes()
            return ret
        else:
            assert self.srcpath
            return open(self.srcpath, "rb").read()


DependsDict = Dict[ContentPath, Tuple[ContentSrc, Set[ContentPath], Set[str]]]


def repr_contentpath(path: ContentPath) -> str:
    return posixpath.join(*(path[0]), path[1])


def to_posixpath(path: str) -> str:
    spath = str(path)
    spath = spath.replace("\\", "/")
    if spath:
        spath = posixpath.normpath(spath)  # A/B/C/../D -> A/B/D
    return spath


def to_pathtuple(dir: Union[str, PathTuple]) -> PathTuple:
    if isinstance(dir, tuple):
        return dir

    spath = to_posixpath(dir).strip("/")
    if not spath:
        return ()

    spath = posixpath.normpath(spath)
    return tuple(spath.split("/"))


def to_contentpath(path: Union[str, ContentPath]) -> ContentPath:
    if isinstance(path, tuple):
        return path

    spath = path.replace("\\", "/")
    spath = posixpath.normpath(spath)

    for c in spath.split("/"):
        if set(c.strip()) == set("."):
            raise ValueError("Invalid path: {path}")

    dir, file = posixpath.split(spath)

    assert file
    tp = to_pathtuple(dir)
    return (tp, file)


def parse_path(path: str, cwd: PathTuple) -> ContentPath:
    path = to_posixpath(path)

    if not path.startswith("/"):
        curdir = "/".join(cwd) or "/"
        path = posixpath.join(curdir, path)

    return to_contentpath(path)


def parse_dir(path: str, cwd: PathTuple) -> PathTuple:
    if isinstance(path, tuple):
        return path

    path = to_posixpath(path)

    if not path.startswith("/"):
        curdir = "/".join(cwd) or "/"
        path = posixpath.join(curdir, path)

    return to_pathtuple(path)


class OutputInfo(NamedTuple):
    contentpath: ContentPath
    filename: Path
    url: str
    title: str
    date: Union[datetime.date, datetime.datetime, None]
    updated: Union[datetime.date, datetime.datetime, None]
    sitemap: bool
    sitemap_priority: float


BuildResult = List[Tuple[ContentSrc, Set[ContentPath], Sequence[OutputInfo]]]
