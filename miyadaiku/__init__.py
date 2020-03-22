from typing import (
    Dict,
    Tuple,
    NamedTuple,
)
import pkg_resources
import tzlocal  # type: ignore

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
    metadata: Dict
    contentpath: ContentPath
    mtime: float

    def read(self, bin: bool):
        if not bin:
            if self.package:
                return pkg_resources.resource_string(self.package, self.srcpath)
            else:
                return open(self.srcpath).read()
        else:
            if self.package:
                return pkg_resources.resource_stream(self.package, self.srcpath).read()
            else:
                return open(self.srcpath, "rb").read()
