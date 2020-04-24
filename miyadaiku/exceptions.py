from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Any, cast
from . import repr_contentpath, ContentPath

if TYPE_CHECKING:
    import miyadaiku.contents

def contentpathname(contentpath:Any)->str:
    if isinstance(contentpath, tuple):
        return repr_contentpath(cast(ContentPath, contentpath))
    else:
        return repr(contentpath)

class ContentNotFound(Exception):
    def __str__(self)->str:
        return f"Content {contentpathname(self.args[0])} is not found"

    def __repr__(self)->str:
        return f"ContentNotFound({contentpathname(self.args[0])})"



class ConfigNotFound(Exception):
    def __str__(self)->str:
        return f"Config {self.args[0]} is not found"

    def __repr__(self)->str:
        return f"ConfigNotFound({self.args[0]})"

