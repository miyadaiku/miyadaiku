from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

from miyadaiku import BuildResult, ContentPath, ContentSrc, OutputInfo

if TYPE_CHECKING:
    from .site import Site
#
#
# def save_sitemap(site:Site, rebuild:bool, outputs:List[Tuple[ContentSrc, Set[ContentPath], Sequence[OutputInfo]]])->None:
#    pass


def save_sitemap(site: Site, rebuild: bool, newdeps: BuildResult) -> None:
    pass
