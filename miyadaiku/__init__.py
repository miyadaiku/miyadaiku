from typing import Dict, Tuple, NamedTuple, Any, Optional, Union
import posixpath
import pkg_resources
import tzlocal

YAML_ENCODING = "utf-8"


CONFIG_FILE = "config.yml"
MODULES_DIR = "modules"
CONTENTS_DIR = "contents"
FILES_DIR = "files"
TEMPLATES_DIR = "templates"
OUTPUTS_DIR = "outputs"

DEFAULT_TIMEZONE = tzlocal.get_localzone().zone
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
]

METADATA_FILE_SUFFIX = ".props.yml"

PathTuple = Tuple[str, ...]
ContentPath = Tuple[PathTuple, str]


class ContentSrc(NamedTuple):
    package: Optional[str]
    srcpath: Optional[str]
    metadata: Dict[str, Any]
    contentpath: ContentPath
    mtime: float = 0.0

    def repr_filename(self) -> str:
        if self.package:
            return f"{self.package}!{self.srcpath}"
        else:
            return f"{self.srcpath}"

    def is_package(self) -> bool:
        return bool(self.package)

    def read_text(self, encoding: str = "utf-8") -> str:
        if self.package and self.srcpath:
            ret = pkg_resources.resource_string(self.package, self.srcpath)
            return ret.decode(encoding)
        else:
            assert self.srcpath
            return open(self.srcpath).read()

    def read_bytes(self) -> bytes:
        if self.package and self.srcpath:
            return pkg_resources.resource_string(self.package, self.srcpath)
        else:
            assert self.srcpath
            return open(self.srcpath, "rb").read()


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
    path = to_posixpath(path)

    if not path.startswith("/"):
        curdir = "/".join(cwd) or "/"
        path = posixpath.join(curdir, path)

    return to_pathtuple(path)

