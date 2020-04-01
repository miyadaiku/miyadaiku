from __future__ import annotations

from typing import Optional, Any
from miyadaiku import ContentSrc, PathTuple
from . import site
from . import config


class Content:
    _filename = None
    updated = False

    def __init__(self, src: ContentSrc, body: Optional[str]) -> None:
        self.src = src
        self.body = body

    def __str__(self) -> str:
        return f"<{self.__class__.__module__}.{self.__class__.__name__} {self.src.srcpath}>"

    def get_body(self) -> bytes:
        if self.body is None:
            return self.src.read_bytes()
        else:
            return self.body.encode("utf-8")

    def get_parent(self) -> PathTuple:
        return self.src.contentpath[0]

    _omit = object()

    def get_metadata(self, site: "site.Site", name: str, default: Any = _omit) -> Any:
        methodname = f"metadata_{name}"
        method = getattr(self, methodname, None)
        if method:
            return method(site, name, default)

        if name in self.src.metadata:
            return config.format_value(name, self.src.metadata.get(name))

        dirname = self.get_parent()
        if default is self._omit:
            return site.config.get(dirname, name)
        else:
            return site.config.get(dirname, name, default)


class BinContent(Content):
    pass


class HTMLContent(Content):
    pass


class Article(Content):
    pass


class Snippet(HTMLContent):
    pass


class IndexPage(Content):
    pass


class FeedPage(Content):
    pass


CONTENT_CLASSES = {
    "binary": BinContent,
    "snippet": Snippet,
    "article": Article,
    "index": IndexPage,
    "feed": FeedPage,
}


def build_content(contentsrc: ContentSrc, body: Optional[str]) -> Content:
    cls = CONTENT_CLASSES[contentsrc.metadata["type"]]
    return cls(contentsrc, body)
