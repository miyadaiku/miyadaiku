from __future__ import annotations

from typing import Optional, Any, TYPE_CHECKING, Union, List, Dict
import re
import unicodedata
import urllib.parse
from bs4 import BeautifulSoup # type: ignore
from pathlib import PurePosixPath

from miyadaiku import ContentSrc, PathTuple
from . import site
from . import config
from . import context

class Content:
    src: ContentSrc
    body: Optional[str]

    def __init__(self, src: ContentSrc, body: Optional[str]) -> None:
        self.src = src
        self.body = body

    def __str__(self) -> str:
        return f"<{self.__class__.__module__}.{self.__class__.__name__} {self.src.srcpath}>"

    @property
    def has_jinja(self)->bool:
        return bool(self.src.metadata.get('has_jinja'))

    def repr_filename(self)->str:
        return repr(self)

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

    def build_html(self, context:context.OutputContext)->Union[None, str]:
        return None

    def get_jinja_vars(self, ctx: context.OutputContext, content: Content) -> Dict[str, Any]:

        ret = {}
        for name in content.get_metadata(ctx.site, "imports"):
            template = ctx.site.jinjaenv.get_template(name)
            fname = name.split("!", 1)[-1]
            modulename = PurePosixPath(fname).stem
            ret[modulename] = template.module

        ret["page"] = context.ContentProxy(ctx, ctx.site.files.get_content(ctx.contentpath))
        ret["content"] = context.ContentProxy(ctx, content)

        ret["contents"] = context.ContentsProxy(ctx)
        ret["config"] = context.ConfigProxy(ctx)

        return ret



class BinContent(Content):
    pass


class HTMLContent(Content):
    def build_html(self, ctx: context.OutputContext)->str:
        ctx.add_depend(self)
        ret = ctx.get_html_cache(self)
        if ret is not None:
            return ret.html

        if self.has_jinja:
            html = self.generate_html(ctx)
        else:
            html = self.body or ''
    
        htmlinfo = self._set_header_id(ctx, html)
        ctx.set_html_cache(self, htmlinfo)

        return htmlinfo.html


    def generate_html(self, ctx: context.OutputContext)->str:
        src = self.body or ''
        html = context.eval_jinja(ctx, self, 'html', src, {})

        return html


    def _set_header_id(self, ctx:context.OutputContext, htmlsrc:str)->context.HTMLInfo:

        soup = BeautifulSoup(htmlsrc, 'html.parser')
        headers:List[context.HTMLIDInfo] = []
        header_anchors:List[context.HTMLIDInfo] = []
        fragments:List[context.HTMLIDInfo] = []
        target_id:Union[str, None] = None

        slugs = set()

        for c in soup.recursiveChildGenerator():
            if c.name and ('header_target' in (c.get('class', '') or [])):
                target_id = c.get('id', None)

            elif re.match(r'h\d', c.name or ''):
                contents = c.text

                if target_id:
                    fragments.append(context.HTMLIDInfo(target_id, c.name, contents))
                    target_id = None

                slug = unicodedata.normalize('NFKC', c.text[:40])
                slug = re.sub(r'[^\w?.]', '', slug)
                slug = urllib.parse.quote_plus(slug)

                n = 1
                while slug in slugs:
                    slug = f'{slug}_{n}'
                    n += 1
                slugs.add(slug)

                id = f'h_{slug}'
                anchor_id = f'a_{slug}'

                parent = c.parent
                if (parent.name) != 'div' or ('md_header_block' not in parent.get('class', [])):
                    parent = soup.new_tag('div', id=id, **{'class': 'md_header_block'})
                    parent.insert(0, soup.new_tag('a', id=anchor_id,
                                                  **{'class': 'md_header_anchor'}))
                    c.wrap(parent)
                else:
                    parent['id'] = id
                    parent.a['id'] = anchor_id

                headers.append(context.HTMLIDInfo(id, c.name, contents))
                header_anchors.append(context.HTMLIDInfo(anchor_id, c.name, contents))

        return context.HTMLInfo(str(soup), headers, header_anchors, fragments)




class Article(HTMLContent):
    pass


class Snippet(HTMLContent):
    pass


class IndexPage(HTMLContent):
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
