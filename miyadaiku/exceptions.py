from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Any, cast
import traceback

from jinja2 import Environment
import jinja2.exceptions


from . import repr_contentpath, ContentPath

if TYPE_CHECKING:
    import miyadaiku.contents


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

def nthlines(src, lineno):
    if not src:
        return ''
    src = src.split('\n')
    f = max(0, lineno - 3)
    lines = []
    for n in range(f, min(f + 5, len(src))):
        if n == (lineno - 1):
            lines.append('  >>> ' + src[n])
        else:
            lines.append('      ' + src[n])

    lines = "\n".join(lines).rstrip() + '\n'
    return lines

def _get_frame(exc:Exception, filename):
    tbs = list(traceback.walk_tb(exc.__traceback__))
    tbs.reverse()
    for tb in tbs:
        if tb[0].f_code.co_filename == filename:
            return tb

def _get_src(e: Exception, filename:str, src:str):
    frame = _get_frame(e, filename)
    if frame:
        lineno = frame[1]
        return lineno, nthlines(src, lineno)
    return 0, ''



class JinjaEvalError(Exception):
    def __init__(self, e:Exception):
        super().__init__(str(e))

        self.errors = []

    def add_error_from_src(self, e: Exception, filename:str, src:str):
        lineno, src = _get_src(e, filename, src)
        self.errors.insert(0, (filename, lineno, src))

    def add_syntaxerrorr_from_src(self, e:jinja2.exceptions.TemplateSyntaxError, filename:str, src:str):
        src = nthlines(src, e.lineno)
        self.errors.insert(0, (filename, e.lineno, src))


    def add_error_from_template(self, e: Exception, env:Environ, templatename:str):
        try:
            src = env.loader.get_source(env, templatename)[0]
        except jinja2.exceptions.TemplateNotFound:
            src = ''

        lineno, src = _get_src(e, templatename, src)
        self.errors.insert(0, (templatename, lineno, src))

    def add_syntaxerrorr_from_template(self, e:jinja2.exceptions.TemplateSyntaxError, env:Environ, templatename:str):
        try:
            src = env.loader.get_source(env, templatename)[0]
        except jinja2.exceptions.TemplateNotFound:
            src = ''

        src = nthlines(src, e.lineno)
        self.errors.insert(0, (templatename, e.lineno, src))
