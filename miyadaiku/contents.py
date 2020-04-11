from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union, cast
import re
import unicodedata
from pathlib import PurePosixPath, Path
import datetime, os
import posixpath
import urllib.parse
import pytz
from bs4 import BeautifulSoup
from bs4.element import NavigableString
import markupsafe

from miyadaiku import ContentSrc, PathTuple, METADATA_FILE_SUFFIX
from . import site
from . import config
from . import context


class Content:
    use_abs_path = False

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

    def _get_config_metadata(
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
            return method(site, default)

        return self._get_config_metadata(site, name, default)

    def metadata_date(self, site: site.Site, default: Any) -> Any:
        date = self._get_config_metadata(site, "date")
        if not date:
            return
        tz = self.get_metadata(site, "tzinfo")
        return date.astimezone(tz)

    def metadata_title(self, site: site.Site, default: Any) -> str:
        title = self._get_config_metadata(site, "title", "")
        if not title:
            return os.path.splitext(self.src.contentpath[1])[0]
        return cast(str, title)

    def metadata_tzinfo(self, site: site.Site, default: Any) -> datetime.tzinfo:
        timezone = self.get_metadata(site, "timezone")
        return pytz.timezone(timezone)


    def metadata_parents_dirs(
        self, site: site.Site, default: Any
    ) -> List[Tuple[str, ...]]:
        ret: List[Tuple[str, ...]] = [()]
        for dirname in self.src.contentpath[0]:
            ret.append(ret[-1] + (dirname,))
        return ret


    def metadata_stem(self, site: site.Site, default: Any) -> str:
        stem = self._get_config_metadata(site, "stem", None)
        if stem is not None:
            return cast(str, stem)

        name = self.src.contentpath[1]
        if not name:
            return ""
        d, name = posixpath.split(name)
        return posixpath.splitext(name)[0]

    def metadata_ext(self, site: site.Site, default: Any) -> str:
        ext = self._get_config_metadata(site, "ext", None)
        if ext is not None:
            return cast(str, ext)

        name = self.src.contentpath[1]
        if not name:
            return ""
        d, name = posixpath.split(name)
        return posixpath.splitext(name)[1]


    def _generate_filename(self, ctx: context.OutputContext, pageargs:Dict[Any, Any]) -> str:
        filename_templ = self.get_metadata(ctx.site, "filename_templ")
        filename_templ = (
            "{% autoescape false %}" + filename_templ + "{% endautoescape %}"
        )

        args = self.get_jinja_vars(ctx)
        ret = context.eval_jinja(ctx, self, "filename", filename_templ, args)
        return ret

    def _pagearg_to_tuple(self, pageargs:Dict[Any, Any])->Tuple[Any, ...]:
        return ()

    def build_filename(self, ctx: context.OutputContext, pageargs:Dict[Any, Any]) -> str:
        tp_pagearg = self._pagearg_to_tuple(pageargs)

        cached = ctx.get_filename_cache(self, tp_pagearg)
        if cached:
            return cached
        filename = self._get_config_metadata(ctx.site, "filename", "")
        if filename:
            ctx.set_filename_cache(self, tp_pagearg, filename)
            return cast(str, filename)

        ret = self._generate_filename(ctx, pageargs)
        ctx.set_filename_cache(self, tp_pagearg, ret)
        return ret

    def build_output_path(self, ctx: context.OutputContext, pageargs:Dict[Any, Any]) -> str:
        filename = self.build_filename(ctx, pageargs)
        return posixpath.join(*self.src.contentpath[0], filename)

    def build_url(
        self,
        ctx: context.OutputContext,
        pageargs:Dict[Any, Any]
    ) -> str:
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
        return cast(str, urllib.parse.urljoin(site_url, path))


    def build_html(self, context: context.OutputContext) -> Union[None, str]:
        return None

    def build_abstract(
        self, context: context.OutputContext, abstract_length: Optional[int] = None
    ) -> Union[None, str]:
        return None

    def get_headertext(
        self, ctx: context.OutputContext, fragment: str
    ) -> Optional[str]:
        return None

    def get_jinja_vars(
        self, ctx: context.OutputContext
    ) -> Dict[str, Any]:

        ret = {}
        for name in self.get_metadata(ctx.site, "imports"):
            template = ctx.site.jinjaenv.get_template(name)
            fname = name.split("!", 1)[-1]
            modulename = PurePosixPath(fname).stem
            ret[modulename] = template.module

        ret["page"] = context.ContentProxy(
            ctx, ctx.site.files.get_content(ctx.contentpath)
        )
        ret["content"] = context.ContentProxy(ctx, self)

        ret["contents"] = context.ContentsProxy(ctx)
        ret["config"] = context.ConfigProxy(ctx)

        return ret

#    def path_to(
#        self,
#        ctx: context.OutputContext,
#        target: Content,
#        pageargs: Dict[Any, Any],
#        *,
#        fragment: Optional[str] = None,
#        abs_path: Optional[bool] = None,
#    ) -> str:
#        fragment = f"#{markupsafe.escape(fragment)}" if fragment else ""
#
#        target_url = target.build_url(ctx, pageargs)
#        if abs_path or self.use_abs_path:
#            return target_url + fragment
#
#        target_parsed = urllib.parse.urlsplit(target_url)
#
#        my_parsed = urllib.parse.urlsplit(self.build_url(ctx, pageargs))
#
#        # return abs url if protocol or server differs
#        if (target_parsed.scheme != my_parsed.scheme) or (
#            target_parsed.netloc != my_parsed.netloc
#        ):
#            return target_url + fragment
#
#        my_dir = posixpath.dirname(my_parsed.path)
#        if my_dir == target_parsed.path:
#            ret_path = my_dir
#        else:
#            ret_path = posixpath.relpath(target_parsed.path, my_dir)
#
#        if target_parsed.path.endswith("/") and (not ret_path.endswith("/")):
#            ret_path = ret_path + "/"
#        return ret_path + fragment

#    def link_to(
#        self,
#        ctx: context.OutputContext,
#        target: Content,
#        pageargs: Dict[Any, Any],
#        *,
#        text: Optional[str] = None,
#        fragment: Optional[str] = None,
#        abs_path: bool = False,
#        attrs: Optional[Dict[str, Any]] = None,
#    ) -> str:
#        if text is None:
#            if fragment:
#                text = target.get_headertext(ctx, fragment)
#                if text is None:
#                    raise ValueError(f"Cannot find fragment: {fragment}")
#
#            if not text:
#                text = markupsafe.escape(target.get_metadata(ctx.site, "title"))
#
#        else:
#            text = markupsafe.escape(text or "")
#
#        s_attrs = []
#        if attrs:
#            for k, v in attrs.items():
#                s_attrs.append(f"{markupsafe.escape(k)}='{markupsafe.escape(v)}'")
#        path = markupsafe.escape(
#            self.path_to(
#                ctx,
#                target,
#                pageargs,
#                fragment=fragment,
#                abs_path=abs_path,
#            )
#        )
#        return markupsafe.Markup(f"<a href='{path}' { ' '.join(s_attrs) }>{text}</a>")


class BinContent(Content):
    pass


class HTMLContent(Content):
    def metadata_ext(self, site: site.Site, default: Any) -> str:
        ext = self._get_config_metadata(site, "ext", None)
        if ext is not None:
            return cast(str, ext)

        return ".html"

    def generate_metadata_file(self, site: site.Site) -> None:
        if not self.get_metadata(site, "generate_metadata_file"):
            return

        if self.src.is_package():
            return
        dir, fname = os.path.split(self.src.srcpath)
        metafilename = Path(dir) / (fname + METADATA_FILE_SUFFIX)
        if metafilename.exists():
            return
        tz: datetime.tzinfo = self.get_metadata(site, "tzinfo")
        date = datetime.datetime.now().astimezone(tz).replace(microsecond=0)
        datestr = date.isoformat(timespec="seconds")
        yaml = f"""
date: {datestr}
"""
        metafilename.write_text(yaml, "utf-8")

        self.src.metadata["date"] = datestr

    def _generate_html(self, ctx: context.OutputContext) -> str:
        src = self.body or ""
        args = self.get_jinja_vars(ctx)
        html = context.eval_jinja(ctx, self, "html", src, args)

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
        ret = ctx.get_html_cache(self, ())
        if ret is not None:
            return ret.html

        if self.has_jinja:
            html = self._generate_html(ctx)
        else:
            html = self.body or ""

        htmlinfo = self._set_header_id(ctx, html)
        ctx.set_html_cache(self, (), htmlinfo)

        return htmlinfo.html

    _in_get_headers = False

    def _get_headers(
        self, ctx: context.OutputContext
    ) -> Tuple[
        List[context.HTMLIDInfo], List[context.HTMLIDInfo], List[context.HTMLIDInfo]
    ]:
        if self._in_get_headers:
            return [], [], []

        self._in_get_headers = True

        try:
            ret = ctx.get_html_cache(self, ())
            if ret is not None:
                return ret.headers, ret.header_anchors, ret.fragments

            self.build_html(ctx)
            ret = ctx.get_html_cache(self, ())
            assert ret
            return ret.headers, ret.header_anchors, ret.fragments

        finally:
            self._in_get_headers = False

    def build_abstract(
        self, context: context.OutputContext, abstract_length: Optional[int] = None
    ) -> str:
        html = self.build_html(context)
        soup = BeautifulSoup(html, "html.parser")

        for elem in soup(["head", "style", "script", "title"]):
            elem.extract()

        if abstract_length is None:
            abstract_length = self.get_metadata(context.site, "abstract_length")

        if abstract_length == 0:
            return str(soup)

        slen = 0
        gen = soup.recursiveChildGenerator()
        for c in gen:
            if isinstance(c, NavigableString):
                curlen = len(c.strip())
                if slen + curlen > abstract_length:
                    last_c = c
                    valid_len = abstract_length - slen - curlen
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

    def get_headers(self, ctx: context.OutputContext) -> List[context.HTMLIDInfo]:
        headers, header_anchors, fragments = self._get_headers(ctx)
        return headers

    def get_header_anchors(
        self, ctx: context.OutputContext
    ) -> List[context.HTMLIDInfo]:
        headers, header_anchors, fragments = self._get_headers(ctx)
        return header_anchors

    def get_fragments(self, ctx: context.OutputContext) -> List[context.HTMLIDInfo]:
        headers, header_anchors, fragments = self._get_headers(ctx)
        return fragments

    def get_headertext(
        self, ctx: context.OutputContext, fragment: str
    ) -> Optional[str]:

        if self._in_get_headers:
            return "!!!! Circular reference detected !!!"

        headers, header_anchors, fragments = self._get_headers(ctx)
        for id, elem, text in fragments:
            if id == fragment:
                return text

        for id, elem, text in headers:
            if id == fragment:
                return text

        for id, elem, text in header_anchors:
            if id == fragment:
                return text

        return None


class Article(HTMLContent):
    pass


class Snippet(HTMLContent):
    pass


class IndexPage(Content):
    def _pagearg_to_tuple(self, pageargs:Dict[Any, Any])->Tuple[Any, ...]:
        return (pageargs.get('cur_page'), pageargs.get('group_value'))

    def _generate_filename(self, ctx: context.OutputContext, pageargs:Dict[Any, Any]) -> str:
        value = str(pageargs.get('group_value', ''))
        value = re.sub(r'[@/\\: \t]', lambda m: f'@{ord(m[0]):02x}', value)

        curpage = pageargs.get('cur_page', 1)

        groupby = self.get_metadata(ctx.site, 'groupby', None)
        if groupby:
            if curpage  == 1:
                filename_templ = self.get_metadata(ctx.site, 'indexpage_group_filename_templ')
            else:
                filename_templ = self.get_metadata(ctx.site, 'indexpage_group_filename_templ2')
        else:
            if curpage  == 1:
                filename_templ = self.get_metadata(ctx.site, 'indexpage_filename_templ')
            else:
                filename_templ = self.get_metadata(ctx.site, 'indexpage_filename_templ2')

        filename_templ = "{% autoescape false %}" + filename_templ + "{% endautoescape %}"

        args = self.get_jinja_vars(ctx)
        args.update(pageargs)

        ret = context.eval_jinja(ctx, self, "filename", filename_templ, args)
        return ret


class FeedPage(Content):
    use_abs_path = True


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
