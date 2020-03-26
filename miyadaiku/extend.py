from typing import Dict, Callable
from miyadaiku.hooks import *

_jinja_globals:Dict[str, Callable] = {}


def jinja_global(f:Callable)->Callable:
    _jinja_globals[f.__name__] = f
    return f
