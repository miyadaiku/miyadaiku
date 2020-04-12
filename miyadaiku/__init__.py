from typing import Dict, Tuple, NamedTuple, Any
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
    package: str
    srcpath: str
    metadata: Dict[str, Any]
    contentpath: ContentPath
    mtime: float = 0.0

    def repr_filename(self) -> str:
        if self.package:
            return f"{self.package}!{self.srcpath}"
        else:
            return self.srcpath

    def is_package(self) -> bool:
        return bool(self.package)

    def read_text(self, encoding: str = "utf-8") -> str:
        if self.package:
            ret = pkg_resources.resource_string(self.package, self.srcpath)
            return ret.decode(encoding)
        else:
            return open(self.srcpath).read()

    def read_bytes(self) -> bytes:
        if self.package:
            return pkg_resources.resource_string(self.package, self.srcpath)
        else:
            return open(self.srcpath, "rb").read()


def to_contentpath(path: str) -> ContentPath:
    spath = str(path)
    spath = spath.replace("\\", "/").strip("/")
    spath  = posixpath.normpath(spath)
    ret = spath.split("/")

    for c in ret:
        if set(c.strip()) == set("."):
            raise ValueError("Invalid path: {path}")

    dir = tuple(ret[:-1])
    return (dir, ret[-1])


def parse_path(path: str, cwd: PathTuple) -> ContentPath:
    path = path.replace("\\", "/")
    dir, name = posixpath.split(path)

    if not dir.startswith("/"):
        curdir = "/".join(cwd) or "/"
        dir = posixpath.join(curdir, dir)

    dir = posixpath.normpath(dir)  # A/B/C/../D -> A/B/D
    path = posixpath.join(dir, name)

    return to_contentpath(path)
