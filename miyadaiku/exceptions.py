from __future__ import annotations

import traceback
from types import FrameType
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, cast

import jinja2.exceptions
from jinja2 import Environment

from . import ContentPath, repr_contentpath

if TYPE_CHECKING:
    pass


def contentpathname(contentpath: Any) -> str:
    if isinstance(contentpath, tuple):
        return repr_contentpath(cast(ContentPath, contentpath))
    else:
        return repr(contentpath)


class ContentNotFound(Exception):
    def __str__(self) -> str:
        return f"Content {contentpathname(self.args[0])} is not found"

    def __repr__(self) -> str:
        return f"ContentNotFound({contentpathname(self.args[0])})"


class ConfigNotFound(Exception):
    def __str__(self) -> str:
        return f"Config {self.args[0]} is not found"

    def __repr__(self) -> str:
        return f"ConfigNotFound({self.args[0]})"


# if not isinstance(e, MiyadaikuBuildError):
#    return MiyadaikuBuildError(e, page, filename, src)
#


def nthlines(src: str, lineno: int) -> str:
    if not src:
        return ""
    srclines = src.split("\n")
    f = max(0, lineno - 3)
    lines = []
    for n in range(f, min(f + 5, len(srclines))):
        if n == (lineno - 1):
            lines.append("  >>> " + srclines[n])
        else:
            lines.append("      " + srclines[n])

    return "\n".join(lines).rstrip() + "\n"


def _get_frame(exc: Exception, filename: str) -> Optional[Tuple[FrameType, int]]:
    tbs = list(traceback.walk_tb(exc.__traceback__))
    tbs.reverse()
    for tb in tbs:
        if tb[0].f_code.co_filename == filename:
            return tb
    return None


def _get_src(e: Exception, filename: str, src: str) -> Tuple[int, str]:
    frame = _get_frame(e, filename)
    if frame:
        lineno = frame[1]
        return lineno, nthlines(src, lineno)
    return 0, ""


class JinjaEvalError(Exception):
    errors: List[Tuple[str, int, str]]

    def __init__(self, e: Exception) -> None:
        super().__init__(str(e))

        self.errors = []

    def __str__(self) -> str:
        errors = []
        for filename, lineno, src in self.errors:
            s = f"  {filename}:{lineno}\n{src}\n"
            errors.append(s)

        errsrc = "\n".join(errors)
        return f"{self.args[0]}\n{errsrc}"

    def __repr__(self) -> str:
        return f"JinjaEvalError({repr(self.args[0])})"

    def add_error_from_src(self, e: Exception, filename: str, src: str) -> None:
        lineno, src = _get_src(e, filename, src)
        self.errors.insert(0, (filename, lineno, src))

    def add_syntaxerrorr_from_src(
        self, e: jinja2.exceptions.TemplateSyntaxError, filename: str, src: str
    ) -> None:
        src = nthlines(src, e.lineno)
        self.errors.insert(0, (filename, e.lineno, src))

    def add_error_from_template(
        self, e: Exception, env: Environment, templatename: str
    ) -> None:
        try:
            src = env.loader.get_source(env, templatename)[0]  # type: ignore
        except jinja2.exceptions.TemplateNotFound:
            src = ""

        lineno, src = _get_src(e, templatename, src)
        self.errors.insert(0, (templatename, lineno, src))

    def add_syntaxerrorr_from_template(
        self,
        e: jinja2.exceptions.TemplateSyntaxError,
        env: Environment,
        templatename: str,
    ) -> None:
        try:
            src = env.loader.get_source(env, templatename)[0]  # type: ignore
        except jinja2.exceptions.TemplateNotFound:
            src = ""

        src = nthlines(src, e.lineno)
        self.errors.insert(0, (templatename, e.lineno, src))
