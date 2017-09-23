
from miyadaiku.core.hooks import *

_jinja_globals = {}


def jinja_global(f):
    _jinja_globals[f.__name__] = f
    return f
