from __future__ import annotations

import binascii
import copy
import datetime
import os
import posixpath
import re
import string
import unicodedata
import urllib.parse
from pathlib import Path, PurePosixPath
from typing import Any, Counter, Dict, List, Optional, Tuple, cast

import pytz
from bs4 import BeautifulSoup
from bs4.element import NavigableString

from miyadaiku import METADATA_FILE_SUFFIX, ContentSrc, PathTuple, repr_contentpath

from . import config, context, extend, site
from .jinjaenv import safepath

# https://stackoverflow.com/a/2267446
digs = string.digits + string.ascii_letters


def int2base(x: int, base: int) -> str:
    if x < 0:
        sign = -1
    elif x == 0:
        return digs[0]
    else:
        sign = 1

    x *= sign
    digits = []

    while x:
        digits.append(digs[int(x % base)])
        x = int(x / base)

    if sign < 0:
        digits.append("-")

    digits.reverse()

    return "".join(digits)


class Content:
    use_abs_path = False

    src: ContentSrc
    body: Optional[bytes]

    def __init__(self, src: ContentSrc, body: Optional[bytes]) -> None:
        self.src = src
        self.body = body

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} at {hex(id(self))} {self.src.srcpath}>"

    def repr_filename(self) -> str:
        return repr(self)

    def generate_metadata_file(self, site: site.Site) -> None:
        if not self.get_metadata(site, "generate_metadata_file"):
            return

        if self.src.is_package():
            return
        if not self.src.srcpath:
            return

        dir, fname = os.path.split(self.src.srcpath)
        metafilename = Path(dir) / (fname + METADATA_FILE_SUFFIX)
        if metafilename.exists():
            return
        tz = self.get_metadata(site, "tzinfo")
        date = tz.localize(datetime.datetime.now()).replace(microsecond=0)
        datestr = date.isoformat(timespec="seconds")
        yaml = f"""
date: {datestr}
"""
        metafilename.write_text(yaml, "utf-8")

        self.src.metadata["date"] = datestr

    def get_body(self) -> bytes:
        if self.body is None:
            return self.src.read_bytes()
        else:
            return self.body

    def get_parent(self) -> PathTuple:
        return self.src.contentpath[0]

    _omit = object()

    def get_config_metadata(
        self, site: site.Site, name: str, default: Any = _omit
    ) -> Any:
        if name in self.src.metadata:
            return config.format_value(name, self.src.metadata.get(name))

        dirname = self.get_parent()
        if default is self._omit:
            return site.config.get(dirname, name)
        else:
            return site.config.get(dirname, name, default)

    def get_metadata(self, site: site.Site, name: str, default: Any = _omit) -> Any:
        methodname = f"metadata_{name}"
        method = getattr(self, methodname, None)
        if method:
            return method(site)

        return self.get_config_metadata(site, name, default)

    def metadata_has_jinja(self, site: site.Site) -> Any:
        return self.get_config_metadata(site, "has_jinja")

    def metadata_dirname(self, site: site.Site) -> PathTuple:
        return self.src.contentpath[0]

    def metadata_name(self, site: site.Site) -> str:
        return self.src.contentpath[1]

    def _get_date_from_filename(self, site: site.Site) -> Optional[Any]:
        if self.get_metadata(site, "date_from_filename", False):
            stem = self.get_metadata(site, "stem", "")
            reg = self.get_metadata(site, "templ_date_from_filename", "")
            if stem and reg:
                m = re.search(reg, stem, re.ASCII)
                if m:
                    datestr = m[0]
                    try:
                        return config.format_value("date", datestr)
                    except (ValueError, OverflowError):
                        pass
        return None

    def metadata_date(self, site: site.Site) -> Any:
        date = self.get_config_metadata(site, "date")
        if not date:
            date = self._get_date_from_filename(site)
            if not date:
                return
        if not date.tzinfo:
            tz = self.get_metadata(site, "tzinfo")
            if tz:
                date = tz.localize(date)
            else:
                date = date.astimezone(datetime.timezone.utc)
        return date

    def metadata_updated(self, site: site.Site) -> Any:
        updated = self.get_config_metadata(site, "updated", default=None)
        if updated:
            if not updated.tzinfo:
                tz = self.get_metadata(site, "tzinfo")
                if tz:
                    updated = tz.localize(updated)
                else:
                    updated = updated.astimezone(datetime.timezone.utc)
            return updated

        return self.metadata_date(site)

    def metadata_tzinfo(self, site: site.Site) -> datetime.tzinfo:
        timezone = self.get_metadata(site, "timezone")
        return pytz.timezone(timezone)

    def metadata_parents_dirs(self, site: site.Site) -> List[Tuple[str, ...]]:
        ret: List[Tuple[str, ...]] = [()]
        for dirname in self.src.contentpath[0]:
            ret.append(ret[-1] + (dirname,))
        return ret

    def metadata_stem(self, site: site.Site) -> str:
        stem = self.get_config_metadata(site, "stem", None)
        if stem is not None:
            return cast(str, stem)

        name = self.src.contentpath[1]
        if not name:
            return ""
        d, name = posixpath.split(name)
        return posixpath.splitext(name)[0]

    def metadata_ext(self, site: site.Site) -> str:
        ext = self.get_config_metadata(site, "ext", None)
        if ext is not None:
            return cast(str, ext)

        name = self.src.contentpath[1]
        if not name:
            return ""
        d, name = posixpath.split(name)
        return posixpath.splitext(name)[1]

    def _generate_filename(
        self, ctx: context.OutputContext, pageargs: Dict[Any, Any]
    ) -> str:
        filename_templ = self.get_metadata(ctx.site, "filename_templ")
        filename_templ = (
            "{% autoescape false %}" + filename_templ + "{% endautoescape %}"
        )

        args = self.get_jinja_vars(ctx)
        ret = context.eval_jinja(ctx, self, "filename", filename_templ, args)
        return safepath(ret)

    def _pagearg_to_tuple(self, pageargs: Dict[Any, Any]) -> Tuple[Any, ...]:
        return ()

    def build_filename(
        self, ctx: context.OutputContext, pageargs: Dict[Any, Any]
    ) -> str:
        tp_pagearg = self._pagearg_to_tuple(pageargs)

        cached = ctx.get_filename_cache(self, tp_pagearg)
        if cached:
            return cached
        filename = self.get_config_metadata(ctx.site, "filename", "")
        if filename:
            ctx.set_filename_cache(self, tp_pagearg, filename)
            return cast(str, filename)

        ret = self._generate_filename(ctx, pageargs)
        ctx.set_filename_cache(self, tp_pagearg, ret)
        return ret

    def build_output_path(
        self, ctx: context.OutputContext, pageargs: Dict[Any, Any]
    ) -> str:
        filename = self.build_filename(ctx, pageargs)
        return posixpath.join(*self.src.contentpath[0], filename)

    def build_url(self, ctx: context.OutputContext, pageargs: Dict[Any, Any]) -> str:
        site_url = self.get_metadata(ctx.site, "site_url")
        path = self.get_metadata(ctx.site, "canonical_url")
        if path:
            parsed = urllib.parse.urlsplit(path)
            if parsed.scheme or parsed.netloc:
                return str(path)  # abs url

            if not parsed.path.startswith("/"):  # relative path?
                path = posixpath.join(*self.src.contentpath[0], path)
        else:
            path = self.build_output_path(ctx, pageargs)

            # strip_directory_index is not applied if canonical_url is specified
            directory_index = self.get_metadata(ctx.site, "strip_directory_index")
            if directory_index:  # skip if falsy value (false, empty string, etc.)
                dir, filename = posixpath.split(path)
                if filename == directory_index:
                    path = dir + "/"

        return cast(str, urllib.parse.urljoin(site_url, path))

    def eval_body(self, ctx: context.OutputContext, propname: str) -> str:
        src = (self.body or b"").decode("utf-8")
        src = "{% autoescape false %}" + src + "{% endautoescape %}"
        args = self.get_jinja_vars(ctx)
        ret = context.eval_jinja(ctx, self, propname, src, args)

        return ret

    def _build_html_src(self, ctx: context.OutputContext) -> None:
        ctx.set_cache("html", self, "")

    def _build_html(self, ctx: context.OutputContext) -> None:
        ret = ctx.get_cache("html", self)
        if ret is not None:
            return

        ctx.add_depend(self)
        with ctx.on_build_html(self):
            self._build_html_src(ctx)

    def get_html(self, ctx: context.OutputContext) -> str:
        self._build_html(ctx)
        return cast(str, ctx.get_cache("html", self))

    def get_soup(self, ctx: context.OutputContext) -> Any:
        ret = ctx.get_cache("soup", self)
        if ret:
            return ret

        self._build_html(ctx)
        return ctx.get_cache("soup", self)

    def get_first_header(self, context: context.OutputContext) -> Optional[str]:
        soup = self.get_soup(context)
        if not soup:
            return None

        for elem in soup(re.compile(r"h\d")):
            text = elem.get_text(" ")
            text = text.strip("\xb6 \t\r\n")  # remove ¶ 'Paragraph symbol'
            text = " ".join(text.split())
            if text:
                return str(text)
        return None

    def build_title(
        self, context: context.OutputContext, fallback: Optional[str] = None
    ) -> str:
        title = self.get_config_metadata(context.site, "title", "").strip()
        if title:
            return str(title)

        if not fallback:
            fallback = self.get_metadata(context.site, "title_fallback")

        if fallback and (fallback not in ["filename", "abstract", "header"]):
            raise ValueError(f"Invalid title_fallback: {fallback}")

        if fallback == "header":
            header = self.get_first_header(context)
            if header:
                return header

        if fallback != "filename":
            abstract_len = self.get_metadata(context.site, "title_abstract_len")
            title = self.build_abstract(context, abstract_len, plain=True)
            title = title.replace("\xb6", "").strip()  # remove ¶ 'Paragraph symbol'
            if title:
                return str(title)

        return posixpath.splitext(self.src.contentpath[1])[0]

    def get_metadata_abstract(
        self, context: context.OutputContext, plain: bool = False
    ) -> Optional[str]:
        meta_abstract: str = self.get_metadata(context.site, "abstract_html", None)
        if meta_abstract:
            if plain:
                soup = BeautifulSoup(meta_abstract, "html.parser")
                return " ".join(soup.get_text(" ").split())
            else:
                return meta_abstract

        return None

    def build_abstract(
        self,
        context: context.OutputContext,
        abstract_length: Optional[int] = None,
        plain: bool = False,
    ) -> str:
        abstract = self.get_metadata_abstract(context, plain)
        if abstract is not None:
            return abstract
        return ""

    def get_headers(self, ctx: context.OutputContext) -> List[context.HTMLIDInfo]:
        return []

    def get_header_anchors(
        self, ctx: context.OutputContext
    ) -> List[context.HTMLIDInfo]:
        return []

    def get_fragments(self, ctx: context.OutputContext) -> List[context.HTMLIDInfo]:
        return []

    def get_headertext(
        self, ctx: context.OutputContext, fragment: str
    ) -> Optional[str]:
        return None

    def search_header(self, ctx: context.OutputContext, search: str) -> Optional[str]:
        return None

    def get_jinja_vars(self, ctx: context.OutputContext) -> Dict[str, Any]:

        ret = {}
        for name in self.get_metadata(ctx.site, "imports"):
            template = ctx.jinjaenv.get_template(name)
            fname = name.split("!", 1)[-1]
            modulename = PurePosixPath(fname).stem
            ret[modulename] = template.module

        ret["context"] = ctx
        ret["page"] = context.ContentProxy(
            ctx, ctx.site.files.get_content(ctx.contentpath)
        )
        ret["content"] = context.ContentProxy(ctx, self)
        ret["contents"] = context.ContentsProxy(ctx, self)
        ret["config"] = context.ConfigProxy(ctx, self)
        bases = [context.ContentProxy(ctx, base) for base in ctx.bases[:-1]]
        ret["bases"] = bases
        return ret


class BinContent(Content):
    pass


class HTMLContent(Content):
    def metadata_ext(self, site: site.Site) -> str:
        ext = self.get_config_metadata(site, "ext", None)
        if ext is not None:
            return cast(str, ext)

        return ".html"

    def set_anchors(self, ctx: context.OutputContext, soup: Any) -> Any:
        """
        1. Record ".header_target" elems.
        2. Set id to header elems.
        """

        ids: List[context.HTMLIDInfo] = []
        targets: List[context.HTMLIDInfo] = []
        headers: List[context.HTMLIDInfo] = []
        header_anchors: List[context.HTMLIDInfo] = []

        short_header_id = self.get_config_metadata(ctx.site, "short_header_id")
        gen_ids: Counter[str] = Counter()
        target_id = None

        for c in soup.recursiveChildGenerator():
            if not isinstance(c, str):
                cid = c.get("id", None)
                if cid:
                    ids.append(context.HTMLIDInfo(cid, c.name, c.text))

            if c.name and ("header_target" in (c.get("class", []) or [])):
                target_id = c.get("id", None)
                if target_id:
                    targets.append(context.HTMLIDInfo(target_id, "", ""))

            elif re.match(r"h\d", c.name or ""):
                contents = " ".join(c.text.split() or [""])
                contents = contents.strip("\xb6 \t\r\n")  # remove ¶ 'Paragraph symbol'

                if target_id:
                    targets[-1] = context.HTMLIDInfo(target_id, c.name, contents)
                    target_id = None

                cls = c.get("class", [])
                if "md_header_block" in cls:
                    # Anchor is already inserted
                    id = c.get("id")
                    headers.append(context.HTMLIDInfo(id, c.name, contents))

                    header_anchors.append(context.HTMLIDInfo(id, c.name, contents))
                    continue

                id = c.get("id", None)
                if id is None:
                    slug = f"{repr_contentpath(self.src.contentpath)}_{c.text[:80]}"
                    if short_header_id:
                        id = int2base(binascii.crc32(slug.encode("utf-8")), 62)
                    else:
                        slug = unicodedata.normalize("NFKC", slug)
                        slug = re.sub(r"[^\w]+", "_", slug)

                        id = f"h_{slug}"

                    gen_ids[id] += 1
                    nth = gen_ids[id]
                    if nth != 1:
                        id = f"{id}_{nth-1}"

                    c["id"] = id

                c["class"] = c.get("class", []) + ["md_header_block"]

                headers.append(context.HTMLIDInfo(id, c.name, contents))
                header_anchors.append(
                    context.HTMLIDInfo(id, c.name, contents)
                )  # header_anchors is deprecated

        ctx.set_cache("ids", self, ids)
        ctx.set_cache("targets", self, targets)
        ctx.set_cache("headers", self, headers)
        ctx.set_cache("header_anchors", self, header_anchors)
        return soup

    def _build_html_src(self, ctx: context.OutputContext) -> None:
        if self.get_metadata(ctx.site, "has_jinja"):
            html = self.eval_body(ctx, "html")
        else:
            html = (self.body or b"").decode("utf-8")

        soup = BeautifulSoup(html, "html.parser")

        soup = self.set_anchors(ctx, soup)

        soup = extend.run_post_build_html(ctx, self, soup)

        ctx.set_cache("html", self, str(soup))
        ctx.set_cache("soup", self, soup)

    _in_build_headers = False

    def _build_headers(self, ctx: context.OutputContext) -> None:

        if ctx.get_cache("headers", self) is not None:
            # already built
            return

        if self._in_build_headers:
            return

        self._in_build_headers = True
        try:
            self._build_html(ctx)
        finally:
            self._in_build_headers = False

    def build_abstract(
        self,
        ctx: context.OutputContext,
        abstract_length: Optional[int] = None,
        plain: bool = False,
    ) -> str:

        abstract = self.get_metadata_abstract(ctx, plain)
        if abstract is not None:
            return abstract

        self._build_html(ctx)
        soup = ctx.get_cache("soup", self)
        if not soup:
            return ""

        soup = copy.copy(ctx.get_cache("soup", self))

        for elem in soup(["head", "style", "script", "title"]):
            elem.extract()

        if abstract_length is None:
            abstract_length = ctx.content.get_metadata(ctx.site, "abstract_length")

        def return_abstract() -> str:
            if not plain:
                return str(soup)
            else:
                return " ".join(soup.get_text(" ").split())

        if abstract_length == 0:
            return return_abstract()

        slen = 0
        gen = soup.recursiveChildGenerator()
        for c in gen:
            if isinstance(c, NavigableString):
                for i, char in enumerate(c):
                    if not char.isspace():
                        slen += 1
                        if slen >= abstract_length:
                            valid_len = i + 1
                            break
                else:
                    continue
                break
        else:
            return return_abstract()

        last_c = c
        while c:
            while c.next_sibling:
                c.next_sibling.extract()
            c = c.parent

        last_c.string.replace_with(last_c[:valid_len])
        return return_abstract()

    def get_headers(self, ctx: context.OutputContext) -> List[context.HTMLIDInfo]:
        self._build_headers(ctx)
        headers = ctx.get_cache("headers", self) or []
        return headers

    def get_header_anchors(
        self, ctx: context.OutputContext
    ) -> List[context.HTMLIDInfo]:

        self._build_headers(ctx)
        headers = ctx.get_cache("header_anchors", self) or []
        return headers

    def get_targets(self, ctx: context.OutputContext) -> List[context.HTMLIDInfo]:
        self._build_headers(ctx)
        headers = ctx.get_cache("targets", self) or []
        return headers

    def get_headertext(
        self, ctx: context.OutputContext, fragment: str
    ) -> Optional[str]:

        if self._in_build_headers:
            return "!!!! Circular reference detected !!!"

        for id, elem, text in self.get_headers(ctx):
            if id == fragment:
                return text

        for id, elem, text in self.get_header_anchors(ctx):
            if id == fragment:
                return text

        for id, elem, text in self.get_targets(ctx):
            if id == fragment:
                return text

        for id, elem, text in ctx.get_cache("ids", self) or ():
            if id == fragment:
                return text

        return None

    def search_header(self, ctx: context.OutputContext, search: str) -> Optional[str]:
        if self._in_build_headers:
            return "!!!! Circular reference detected !!!"

        search = search.lower()

        for id, elem, text in self.get_headers(ctx):
            if search in text.lower():
                return id

        for id, elem, text in self.get_header_anchors(ctx):
            if search in text.lower():
                return id

        for id, elem, text in self.get_targets(ctx):
            if search in text.lower():
                return id

        for id, elem, text in ctx.get_cache("ids", self) or ():
            if search in text.lower():
                return id

        return None


class Article(HTMLContent):
    pass


class Snippet(HTMLContent):
    pass


class IndexPage(Content):
    def _pagearg_to_tuple(self, pageargs: Dict[Any, Any]) -> Tuple[Any, ...]:
        return (pageargs.get("cur_page"), pageargs.get("group_value"))

    def _generate_filename(
        self, ctx: context.OutputContext, pageargs: Dict[Any, Any]
    ) -> str:

        curpage = pageargs.get("cur_page", None)
        groupby = self.get_metadata(ctx.site, "groupby", None)

        if groupby:
            if (not curpage) or (curpage == 1):
                filename_templ = self.get_metadata(
                    ctx.site, "indexpage_group_filename_templ"
                )
            else:
                filename_templ = self.get_metadata(
                    ctx.site, "indexpage_group_filename_templ2"
                )
        else:
            if (not curpage) or (curpage == 1):
                filename_templ = self.get_metadata(ctx.site, "indexpage_filename_templ")
            else:
                filename_templ = self.get_metadata(
                    ctx.site, "indexpage_filename_templ2"
                )

        filename_templ = (
            "{% autoescape false %}" + filename_templ + "{% endautoescape %}"
        )

        args = self.get_jinja_vars(ctx)
        args.update(pageargs)

        ret = context.eval_jinja(ctx, self, "filename", filename_templ, args)

        return safepath(ret)


class FeedPage(Content):
    use_abs_path = True

    def metadata_ext(self, site: site.Site) -> str:
        feedtype = self.get_metadata(site, "feedtype")
        if feedtype == "atom":
            return ".xml"
        elif feedtype == "rss":
            return ".rdf"
        else:
            raise ValueError(f"Invarid feed type: {feedtype}")


CONTENT_CLASSES = {
    "binary": BinContent,
    "snippet": Snippet,
    "article": Article,
    "index": IndexPage,
    "feed": FeedPage,
}


def build_content(contentsrc: ContentSrc, body: Optional[bytes]) -> Content:
    cls = CONTENT_CLASSES[contentsrc.metadata["type"]]
    return cls(contentsrc, body)
