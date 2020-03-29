from typing import Dict, Callable, Any
# from miyadaiku.hooks import *

_jinja_globals: Dict[str, Callable[..., Any]] = {}


def jinja_global(f: Callable[..., Any]) -> Callable[..., Any]:
    _jinja_globals[f.__name__] = f
    return f
