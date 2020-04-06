from __future__ import annotations

from typing import Optional, Any, TYPE_CHECKING, Union, List, Dict, cast, Tuple
import re
import unicodedata
import urllib.parse
from pathlib import PurePosixPath, Path
import datetime, os
import posixpath

from bs4 import BeautifulSoup
from bs4.element import NavigableString

from miyadaiku import ContentSrc, PathTuple, METADATA_FILE_SUFFIX
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
    def has_jinja(self) -> bool:
        return bool(self.src.metadata.get("has_jinja"))

    def repr_filename(self) -> str:
        return repr(self)

    def generate_metadata_file(self, site: site.Site) -> None:
        pass

    def get_body(self) -> bytes:
        if self.body is None:
            return self.src.read_bytes()
        else:
            return self.body.encode("utf-8")

    def get_parent(self) -> PathTuple:
        return self.src.contentpath[0]

    _omit = object()

    def get_metadata(self, site: site.Site, name: str, default: Any = _omit) -> Any:
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


    def _generate_filename(self, ctx:context.OutputContext)->str:
        filename_templ = self.get_metadata(ctx.site, 'filename_templ')
        filename_templ = "{% autoescape false %}" + filename_templ + "{% endautoescape %}"


        ret = context.eval_jinja(ctx, self, 'filename', filename_templ, {})
        return ret

    def get_filename(self, ctx: context.OutputContext)->str:
        filename = self.get_metadata(ctx.site, 'filename', None)
        if filename:
            return cast(str, filename)

        return self._generate_filename(ctx)

    def metadata_stem(self, site:site.Site)->str:
        stem = self.get_metadata(site, 'stem', None)
        if stem is not None:
            return cast(str, stem)
        name = self.get_metadata(site, 'name', None)
        if not name:
            return ''
        d, name = posixpath.split(name)
        return cast(str, posixpath.splitext(name)[0])

    def metadata_ext(self, site:site.Site)->str:
        ext = self.get_metadata(site, 'ext', None)
        if ext is not None:
            return cast(str, ext)
        name = self.get_metadata(site, 'name', None)
        if not name:
            return ''
        d, name = posixpath.split(name)
        return cast(str, posixpath.splitext(name)[1])


    def build_html(self, context: context.OutputContext) -> Union[None, str]:
        return None


    def build_abstract(self, context: context.OutputContext, abstract_length:Optional[int]=None)->Union[None, str]:
        return None
    
    def get_jinja_vars(
        self, ctx: context.OutputContext, content: Content
    ) -> Dict[str, Any]:

        ret = {}
        for name in content.get_metadata(ctx.site, "imports"):
            template = ctx.site.jinjaenv.get_template(name)
            fname = name.split("!", 1)[-1]
            modulename = PurePosixPath(fname).stem
            ret[modulename] = template.module

        ret["page"] = context.ContentProxy(
            ctx, ctx.site.files.get_content(ctx.contentpath)
        )
        ret["content"] = context.ContentProxy(ctx, content)

        ret["contents"] = context.ContentsProxy(ctx)
        ret["config"] = context.ConfigProxy(ctx)

        return ret


class BinContent(Content):
    pass


class HTMLContent(Content):
    def generate_metadata_file(self, site: site.Site) -> None:
        if not self.get_metadata(site, "generate_metadata_file"):
            return

        if self.src.is_package():
            return
        dir, fname = os.path.split(self.src.srcpath)
        metafilename = Path(dir) / (fname + METADATA_FILE_SUFFIX)
        if metafilename.exists():
            return
        tz: datetime.tzinfo = self.get_metadata(site, "timezone")
        date = datetime.datetime.now().astimezone(tz).replace(microsecond=0)
        datestr = date.isoformat(timespec="seconds")
        yaml = f"""
date: {datestr}
"""
        metafilename.write_text(yaml, "utf-8")

        self.src.metadata["date"] = datestr

    def _generate_html(self, ctx: context.OutputContext) -> str:
        src = self.body or ""
        html = context.eval_jinja(ctx, self, "html", src, {})

        return html

    def _set_header_id(
        self, ctx: context.OutputContext, htmlsrc: str
    ) -> context.HTMLInfo:

        soup = BeautifulSoup(htmlsrc, "html.parser")
        headers: List[context.HTMLIDInfo] = []
        header_anchors: List[context.HTMLIDInfo] = []
        fragments: List[context.HTMLIDInfo] = []
        target_id: Union[str, None] = None

        slugs = set()

        for c in soup.recursiveChildGenerator():
            if c.name and ("header_target" in (c.get("class", "") or [])):
                target_id = c.get("id", None)

            elif re.match(r"h\d", c.name or ""):
                contents = c.text

                if target_id:
                    fragments.append(context.HTMLIDInfo(target_id, c.name, contents))
                    target_id = None

                slug = unicodedata.normalize("NFKC", c.text[:40])
                slug = re.sub(r"[^\w?.]", "", slug)
                slug = urllib.parse.quote_plus(slug)

                n = 1
                while slug in slugs:
                    slug = f"{slug}_{n}"
                    n += 1
                slugs.add(slug)

                id = f"h_{slug}"
                anchor_id = f"a_{slug}"

                parent = c.parent
                if (parent.name) != "div" or (
                    "md_header_block" not in parent.get("class", [])
                ):
                    parent = soup.new_tag("div", id=id, **{"class": "md_header_block"})
                    parent.insert(
                        0,
                        soup.new_tag(
                            "a", id=anchor_id, **{"class": "md_header_anchor"}
                        ),
                    )
                    c.wrap(parent)
                else:
                    parent["id"] = id
                    parent.a["id"] = anchor_id

                headers.append(context.HTMLIDInfo(id, c.name, contents))
                header_anchors.append(context.HTMLIDInfo(anchor_id, c.name, contents))

        return context.HTMLInfo(str(soup), headers, header_anchors, fragments)

    def build_html(self, ctx: context.OutputContext) -> str:
        ctx.add_depend(self)
        ret = ctx.get_html_cache(self)
        if ret is not None:
            return ret.html

        if self.has_jinja:
            html = self._generate_html(ctx)
        else:
            html = self.body or ""

        htmlinfo = self._set_header_id(ctx, html)
        ctx.set_html_cache(self, htmlinfo)

        return htmlinfo.html

    _in_get_headers = False
    def _get_headers(self, ctx:context.OutputContext)->Tuple[List[context.HTMLIDInfo],List[context.HTMLIDInfo],List[context.HTMLIDInfo]]:
        if self._in_get_headers:
            return [], [], []

        self._in_get_headers = True

        try:
            ret = ctx.get_html_cache(self)
            if ret is not None:
                return ret.headers, ret.header_anchors, ret.fragments

            self.build_html(ctx)
            ret = ctx.get_html_cache(self)
            assert ret
            return ret.headers, ret.header_anchors, ret.fragments

        finally:
            self._in_get_headers = False

    def build_abstract(self, context:context.OutputContext, abstract_length:Optional[int]=None) -> str:
        html = self.build_html(context)
        soup = BeautifulSoup(html, 'html.parser')

        for elem in soup(["head", "style", "script", "title"]):
            elem.extract()

        if abstract_length is None:
            abstract_length = self.get_metadata(context.site, 'abstract_length')

        if abstract_length == 0:
            return str(soup)

        slen = 0
        gen = soup.recursiveChildGenerator()
        for c in gen:
            if isinstance(c, NavigableString):
                curlen = len(c.strip())
                if slen + curlen > abstract_length:
                    last_c = c
                    valid_len = abstract_length - slen-curlen
                    break
                slen += curlen
        else:
            return str(soup)

        while c:
            while c.next_sibling:
                c.next_sibling.extract()
            c = c.parent

        last_c.string.replace_with(last_c[:valid_len])
        return str(soup)

    def get_headers(self, ctx:context.OutputContext)->List[context.HTMLIDInfo]:
        headers, header_anchors, fragments = self._get_headers(ctx)
        return headers

    def get_header_anchors(self, ctx:context.OutputContext)->List[context.HTMLIDInfo]:
        headers, header_anchors, fragments = self._get_headers(ctx)
        return header_anchors

    def get_fragments(self, ctx:context.OutputContext)->List[context.HTMLIDInfo]:
        headers, header_anchors, fragments = self._get_headers(ctx)
        return fragments

    

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
