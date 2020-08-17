import logging
import os
import re
import urllib
from pathlib import Path
from typing import Any, Dict, List, Tuple

from jinja2 import DebugUndefined  # NOQA
from jinja2 import StrictUndefined  # NOQA
from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    PrefixLoader,
    TemplateNotFound,
    make_logging_undefined,
    select_autoescape,
)

import miyadaiku.site

logger = logging.getLogger(__name__)


class PackagesLoader(PrefixLoader):
    delimiter = "!"

    def __init__(self) -> None:
        self._loaders: Dict[str, Any] = {}

    def get_loader(self, template: str) -> Tuple[Any, str]:
        package, *rest = template.split(self.delimiter, 1)
        if not rest:
            raise TemplateNotFound(template)

        if package not in self._loaders:
            self._loaders[package] = PackageLoader(package)

        return self._loaders[package], rest[0]

    def list_templates(self) -> None:
        raise TypeError("this loader cannot iterate over all templates")


EXTENSIONS = ["jinja2.ext.do"]


def safepath(s: str) -> str:
    s = str(s)
    re.sub(r"[@/\\: \t]", lambda m: f"@{ord(m[0]):02x}", s)
    return s


def urlquote(s: str) -> str:
    s = str(s)
    s = urllib.parse.quote_plus(s)
    return s


def create_env(
    site: "miyadaiku.site.Site", themes: List[str], paths: List[Path]
) -> Environment:
    loaders: List[Any] = [PackagesLoader()]
    for path in paths:
        loaders.append(FileSystemLoader(os.fspath(path)))

    loaders.extend([PackageLoader(theme) for theme in themes])
    loaders.append(PackageLoader("miyadaiku.themes.base"))

    env = Environment(
        undefined=make_logging_undefined(logger, DebugUndefined),
        # undefined=make_logging_undefined(logger, StrictUndefined),
        loader=ChoiceLoader(loaders),
        autoescape=select_autoescape(["html", "xml", "j2"]),
        extensions=EXTENSIONS,
    )

    env.globals["str"] = str
    env.globals["list"] = list
    env.globals["tuple"] = tuple
    env.globals["dict"] = dict

    env.globals["site"] = site

    env.globals["len"] = len
    env.globals["repr"] = repr
    env.globals["print"] = print
    env.globals["type"] = type
    env.globals["dir"] = dir
    env.globals["isinstance"] = isinstance
    env.globals["setattr"] = setattr
    env.globals["getattr"] = getattr

    env.filters["urlquote"] = urlquote
    env.filters["safepath"] = safepath

    return env
