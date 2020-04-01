from __future__ import annotations


from typing import (
    TYPE_CHECKING,
    List,
    Type,
    Sequence,
    Tuple,
    Dict,
    Union,
    Any,
)
from abc import abstractmethod
import os, time, random, shutil
from miyadaiku import ContentPath, PathTuple
from pathlib import Path, PurePosixPath

from .context import CONTEXTS
if TYPE_CHECKING:
    from .contents import Content
    from .site import Site
    from .context import BinaryOutput


class Builder:
    contentpath: ContentPath

    @classmethod
    def create_builders(cls, site: Site, content: Content) -> List[Builder]:
        return [cls(content)]

    def __init__(self, content: Content) -> None:
        self.contentpath = content.src.contentpath

    def build(self, site: Site) -> List[Tuple[Path, ContentPath]]:
        content = site.files.get_content(self.contentpath)
        contexttype = CONTEXTS.get(content.src.metadata["type"], BinaryOutput)
        context = contexttype(site, self, self.contentpath)
        return context.build()


def normalize_path(dirname: str) -> str:
    ret = dirname.replace("\\", "/").strip("/")
    letters = (set(p) for p in ret.split("/"))
    for letter in letters:
        if letter == set("."):
            raise ValueError(f"{dirname} contains relative path")
    return ret


def dirname_to_tuple(dirname: Union[str, PathTuple]) -> PathTuple:
    if isinstance(dirname, tuple):
        return dirname

    dirname = normalize_path(dirname)

    if dirname:
        dirname = tuple(dirname.split("/"))
    else:
        dirname = ()
    return dirname


class IndexBuilder(Builder):
    names: Tuple[str, ...]
    items: Sequence[ContentPath]
    cur_page: int
    num_pages: int

    @classmethod
    def create_builders(cls, site: Site, content: Content) -> List[Builder]:
        filters = content.get_metadata(site, "filters", {}).copy()

        filters["type"] = {"article"}
        filters["draft"] = {False}

        dirname = content.get_metadata(site, "directory", "")
        dir = dirname_to_tuple(dirname)

        groupby = content.get_metadata(site, "groupby", None)
        groups = site.files.group_items(
            site, groupby, filters=filters, subdirs=[dir], recurse=True
        )

        n_per_page = int(content.get_metadata(site, "indexpage_max_articles"))
        page_orphan = int(content.get_metadata(site, "indexpage_orphan"))
        indexpage_max_num_pages = int(
            content.get_metadata(site, "indexpage_max_num_pages", 0)
        )

        ret: List[Builder] = []

        for names, group in groups:
            num = len(group)
            num_pages = ((num - 1) // n_per_page) + 1
            rest = num - (num_pages - 1) * n_per_page

            if rest <= page_orphan:
                if num_pages > 1:
                    num_pages -= 1

            if indexpage_max_num_pages:
                num_pages = min(num_pages, indexpage_max_num_pages)

            for page in range(0, num_pages):

                is_last = page == (num_pages - 1)

                f = page * n_per_page
                t = num if is_last else f + n_per_page
                articles = group[f:t]

                ret.append(cls(content, names, articles, page + 1, num_pages))

        return ret

    def __init__(
        self,
        content: Content,
        names: Tuple[str, ...],
        items: Sequence[Content],
        cur_page: int,
        num_pages: int,
    ) -> None:
        super().__init__(content)

        self.names = names
        self.items = [c.src.contentpath for c in items]
        self.cur_page = cur_page
        self.num_pages = num_pages


BUILDERS: Dict[str, Type[Builder]] = {
    "binary": Builder,
    "article": Builder,
    "index": IndexBuilder,
}


def createBuilder(site: Site, content: Content) -> List[Builder]:
    buildercls = BUILDERS.get(content.src.metadata["type"], None)
    if buildercls:
        return buildercls.create_builders(site, content)
    else:
        return []
