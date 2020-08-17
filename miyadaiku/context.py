from __future__ import annotations

import datetime
import os
import posixpath
import random
import shutil
import time
import urllib.parse
import warnings
from abc import abstractmethod
from collections import defaultdict
from functools import update_wrapper
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    DefaultDict,
    Dict,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)
from urllib.parse import urlparse

import jinja2.exceptions
import markupsafe
from feedgenerator import Atom1Feed, Rss201rev2Feed, datetime_safe
from jinja2 import Environment

from miyadaiku import (
    ContentPath,
    PathTuple,
    exceptions,
    parse_dir,
    parse_path,
    repr_contentpath,
)

if TYPE_CHECKING:
    from .contents import Article, Content, FeedPage, IndexPage
    from .site import Site

SAFE_STR = Union[str, markupsafe.Markup]


def to_markupsafe(s: Optional[str]) -> Optional[SAFE_STR]:
    if s is not None:
        if not hasattr(s, "__html__"):
            s = markupsafe.Markup(s)
    return s


def safe_prop(f: Callable[..., Any]) -> property:
    """AttributeError in the function raises TypeError instead.
       This prevents __getattr__() being called in case if error
       in the decorator"""

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return f(*args, **kwargs)
        except AttributeError as e:
            raise TypeError(str(e)) from e

    update_wrapper(wrapper, f)
    return property(wrapper)


class ContentProxy:
    context: OutputContext
    content: Content

    def __init__(self, ctx: OutputContext, content: Content) -> None:
        self.context = ctx
        self.content = content

    def __getattr__(self, name: str) -> Any:
        if hasattr(self.content, name):
            return getattr(self.content, name)

        return self.content.get_metadata(self.context.site, name)

    def set(self, **kwargs: Any) -> str:
        for k, v in kwargs.items():
            setattr(self.content, k, v)

        self.context.invalidate_cache()
        return ""

    @safe_prop
    def title(self) -> str:
        return self.content.build_title(self.context)

    @safe_prop
    def contentpath(self) -> ContentPath:
        return self.content.src.contentpath

    @safe_prop
    def filename(self) -> str:
        return self.content.build_filename(self.context, {})

    @safe_prop
    def abstract(self) -> Union[None, str]:
        return self.get_abstract()

    @safe_prop
    def html(self) -> Union[None, str]:
        ret = self.content.get_html(self.context)
        return to_markupsafe(ret)

    @safe_prop
    def url(self) -> str:
        warnings.warn(
            "content.url is deprecated. Use contenxt.get_url().", DeprecationWarning
        )

        # TODO: should be deprecated
        if self.is_same(self.context):
            pageargs = self.context._build_pagearg()
        else:
            pageargs = {}
        return self.content.build_url(self.context, pageargs)

    @safe_prop
    def output_path(self) -> str:
        return self.content.build_output_path(self.context, {})

    @safe_prop
    def headers(self) -> List[HTMLIDInfo]:
        return self.content.get_headers(self.context)

    @safe_prop
    def header_anchors(self) -> List[HTMLIDInfo]:
        return self.content.get_header_anchors(self.context)

    def build_title(self, fallback: str = "") -> str:
        return self.content.build_title(self.context, fallback)

    def fragments(self, ctx: OutputContext) -> List[HTMLIDInfo]:
        return self.content.get_fragments(self.context)

    def is_same(self, other: OutputContext) -> bool:
        if self.contentpath == other.contentpath:
            return True
        return False

    def eval_body(self) -> Union[None, str]:
        ret = self.content.eval_body(self.context, "body")
        return ret

    _omit = object()

    def has_config(self, name: str) -> bool:
        obj = object()
        ret = self.get_config(name, default=obj)
        if ret is obj:
            return False
        else:
            return True

    def get_config(self, name: str, default: Any = _omit) -> Any:
        if default is self._omit:
            return self.content.get_metadata(self.context.site, name)
        else:
            return self.content.get_metadata(self.context.site, name, default)

    def get_abstract(
        self, abstract_length: Optional[int] = None, plain: bool = False
    ) -> Union[None, str]:
        ret = self.content.build_abstract(self.context, abstract_length, plain=plain)
        return to_markupsafe(ret)

    def get_headertext(self, fragment: str) -> Optional[str]:
        return self.content.get_headertext(self.context, fragment)

    def _load(self, target: str) -> Content:
        assert isinstance(target, str)
        path = parse_path(target, self.content.src.contentpath[0])
        return self.context.site.files.get_content(path)

    def load(self, target: str) -> ContentProxy:
        return ContentProxy(self.context, self._load(target))

    def _to_content(
        self, content: Union[ContentProxy, Content, str, ContentPath]
    ) -> Content:
        if isinstance(content, str):
            return self._load(content)
        elif isinstance(content, ContentProxy):
            return content.content
        elif isinstance(content, tuple):
            return self.context.site.files.get_content(content)
        else:
            return content

    def path(
        self,
        *,
        fragment: Optional[str] = None,
        abs_path: Optional[bool] = None,
        group_value: Optional[Any] = None,
        npage: Optional[int] = None,
    ) -> str:
        return self.context.path_to(
            self.content,
            {"group_value": group_value, "cur_page": npage},
            fragment=fragment,
            abs_path=abs_path,
        )

    def path_to(
        self,
        target: Union[ContentProxy, Content, str, ContentPath],
        *,
        fragment: Optional[str] = None,
        abs_path: Optional[bool] = None,
        group_value: Optional[Any] = None,
        npage: Optional[int] = None,
    ) -> str:

        target_content = self._to_content(target)
        return self.context.path_to(
            target_content,
            {"group_value": group_value, "cur_page": npage},
            fragment=fragment,
            abs_path=abs_path,
        )

    def link(
        self,
        *,
        text: Optional[str] = None,
        fragment: Optional[str] = None,
        search: Optional[str] = None,
        abs_path: bool = False,
        attrs: Optional[Dict[str, Any]] = None,
        group_value: Optional[Any] = None,
        npage: Optional[int] = None,
    ) -> str:
        return self.context.link_to(
            self.content,
            {"group_value": group_value, "npage": npage},
            text=text,
            fragment=fragment,
            search=search,
            abs_path=abs_path,
            attrs=attrs,
        )

    def link_to(
        self,
        target: Union[ContentProxy, Content, str, ContentPath],
        *,
        text: Optional[str] = None,
        fragment: Optional[str] = None,
        search: Optional[str] = None,
        abs_path: bool = False,
        attrs: Optional[Dict[str, Any]] = None,
        group_value: Optional[Any] = None,
        npage: Optional[int] = None,
    ) -> str:
        target_content = self._to_content(target)
        return self.context.link_to(
            target_content,
            {"group_value": group_value, "npage": npage},
            text=text,
            fragment=fragment,
            search=search,
            abs_path=abs_path,
            attrs=attrs,
        )


class ConfigProxy:
    def __init__(self, ctx: "OutputContext", content: Content) -> None:
        self.context = ctx
        self.content = content

    def __getitem__(self, key: str) -> Any:
        return self.get(self.content.src.contentpath[0], key)

    def __getattr__(self, key: str) -> Any:
        return self.get(self.content.src.contentpath[0], key)

    _omit = object()

    def get(
        self, dir: Union[None, str, PathTuple], name: str, default: Any = _omit
    ) -> Any:
        if isinstance(dir, tuple):
            dirtuple = dir
        elif isinstance(dir, str):
            dirtuple = parse_dir(dir, self.content.src.contentpath[0])
        elif dir is None:
            dirtuple = self.content.src.contentpath[0]
        else:
            raise ValueError(f"Invalid dir: {dir}")

        try:
            return self.context.site.config.get(dirtuple, name)
        except exceptions.ConfigNotFound:
            if default is self._omit:
                raise
            return default


class ContentsProxy:
    def __init__(self, ctx: "OutputContext", content: Content) -> None:
        self.context = ctx
        self.content = content

    def __getitem__(self, key: str) -> Any:
        return self.get_content(key)

    def get_content(self, path: str, base: Any = None) -> ContentProxy:
        if not base:
            base = self.content
        contentpath = parse_path(path, base.src.contentpath[0])

        content = self.context.site.files.get_content(contentpath)
        return ContentProxy(self.context, content)

    def get_contents(
        self,
        subdirs: Optional[Sequence[str]] = None,
        recurse: bool = True,
        base: Any = None,
        filters: Optional[Dict[str, Any]] = None,
        excludes: Optional[Dict[str, Any]] = None,
    ) -> Sequence[ContentProxy]:
        subdirs_path = None
        if not base:
            base = self.content
        if subdirs:
            subdirs_path = [
                parse_dir(path, base.src.contentpath[0]) for path in subdirs
            ]
            print(subdirs_path)

        ret = self.context.site.files.get_contents(
            self.context.site,
            filters=filters,
            subdirs=subdirs_path,
            recurse=recurse,
            excludes=excludes,
        )
        return [ContentProxy(self.context, content) for content in ret]

    def group_items(
        self,
        group: str,
        subdirs: Optional[Sequence[str]] = None,
        recurse: bool = True,
        filters: Optional[Dict[str, Any]] = None,
        excludes: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Tuple[str, ...], List[ContentProxy]]]:
        subdirs_path = None
        if subdirs:
            subdirs_path = [
                parse_dir(path, self.content.src.contentpath[0]) for path in subdirs
            ]

        groups = self.context.site.files.group_items(
            self.context.site,
            group,
            filters=filters,
            excludes=excludes,
            subdirs=subdirs_path,
            recurse=recurse,
        )

        ret: List[Tuple[Tuple[str, ...], List[ContentProxy]]] = []

        for groupvalues, contents in groups:
            ret.append(
                (
                    groupvalues,
                    [ContentProxy(self.context, content) for content in contents],
                )
            )
        return ret

    @property
    def categories(self) -> Sequence[str]:
        contents = self.get_contents(filters={"type": {"article"}})
        categories = (getattr(c, "category", None) for c in contents)
        return sorted(set(c for c in categories if c))

    @property
    def tags(self) -> Sequence[str]:
        tags = set()
        for c in self.get_contents(filters={"type": {"article"}}):
            t = getattr(c, "tags", None)
            if t:
                tags.update(t)
        return sorted(tags)


class ConfigArgProxy:
    def __init__(self, context: OutputContext, content: Content) -> None:
        self.context, self.content = (context, content)

    def __getitem__(self, key: str) -> Any:
        return self.context.site.config.get(self.content.src.contentpath[0], key)

    def __getattr__(self, name: str) -> Any:
        return self.context.site.config.get(self.content.src.contentpath[0], name)

    _omit = object()

    def get(self, dirname: str, name: str, default: Any = _omit) -> Any:
        if default is self._omit:
            return self.context.site.config.get(dirname, name)
        else:
            return self.context.site.config.get(dirname, name, default)


MKDIR_MAX_RETRY = 5
MKDIR_WAIT = 0.1


def prepare_output_path(path: Path, directory: PathTuple, filename: str) -> Path:
    dir = path.joinpath(*directory)
    name = filename.strip("/\\")
    dest = os.path.expanduser((dir / name))
    dest = os.path.normpath(dest)

    s = str(path)
    if not dest.startswith(s) or dest[len(s)] not in "\\/":
        raise ValueError(f"Invalid file name: {dest}")

    dirname = os.path.split(dest)[0]
    for i in range(MKDIR_MAX_RETRY):
        if os.path.isdir(dirname):
            break
        try:
            os.makedirs(dirname, exist_ok=True)
        except IOError:
            time.sleep(MKDIR_WAIT * random.random())

    if os.path.exists(dest):
        os.unlink(dest)

    return Path(dest).absolute()


def eval_jinja(
    ctx: OutputContext,
    content: Content,
    propname: str,
    text: str,
    kwargs: Dict[str, Any],
) -> str:

    ctx.add_depend(content)

    args = content.get_jinja_vars(ctx)
    args.update(kwargs)

    filename = f"{repr_contentpath(content.src.contentpath)}#{propname}"

    try:
        template = ctx.jinjaenv.from_string(text)

    except jinja2.exceptions.TemplateSyntaxError as e:
        exc = exceptions.JinjaEvalError(e)
        exc.add_syntaxerrorr_from_src(e, filename, text)
        raise exc

    template.filename = filename

    try:
        return template.render(**kwargs)

    except exceptions.JinjaEvalError as e:
        e.add_error_from_src(e, template.filename, text)
        raise e

    except Exception as e:
        exc = exceptions.JinjaEvalError(e)
        exc.add_error_from_src(e, template.filename, text)
        raise exc


def eval_jinja_template(
    ctx: OutputContext, content: Content, templatename: str, kwargs: Dict[str, Any],
) -> str:

    try:
        template = ctx.jinjaenv.get_template(templatename)

    except jinja2.exceptions.TemplateSyntaxError as e:
        exc = exceptions.JinjaEvalError(e)
        exc.add_syntaxerrorr_from_template(e, ctx.jinjaenv, templatename)
        raise exc

    template.filename = templatename

    args = content.get_jinja_vars(ctx)
    args.update(kwargs)

    try:
        return template.render(**args)

    except exceptions.JinjaEvalError as e:
        e.add_error_from_template(e, ctx.jinjaenv, templatename)
        raise e

    except Exception as e:
        exc = exceptions.JinjaEvalError(e)
        exc.add_error_from_template(e, ctx.jinjaenv, templatename)
        raise exc


class HTMLIDInfo(NamedTuple):
    id: str
    tag: str
    text: str


class HTMLInfo(NamedTuple):
    html: str
    headers: List[HTMLIDInfo]  # ids of header elements
    header_anchors: List[HTMLIDInfo]  # ids of anchor wrapping header elements
    fragments: List[
        HTMLIDInfo
    ]  # ids of header elements specified by header_target class


class OutputContext:
    site: Site
    contentpath: ContentPath
    content: Content
    #    _html_cache: Dict[ContentPath, HTMLInfo]

    depends: Set[ContentPath]

    _filename_cache: Dict[Tuple[ContentPath, Tuple[Any, ...]], str]
    _cache: DefaultDict[str, Dict[ContentPath, Any]]

    def __init__(
        self, site: Site, jinjaenv: Environment, contentpath: ContentPath
    ) -> None:
        self.site = site
        self.jinjaenv = jinjaenv
        self.contentpath = contentpath
        self.content = site.files.get_content(self.contentpath)
        self.depends = set([contentpath])
        self._filename_cache = {}
        self._cache = defaultdict(dict)

    def get_url(self) -> str:
        pageargs = self._build_pagearg()
        return self.content.build_url(self, pageargs)

    def _get_outfilename(self, pagearg: Dict[Any, Any]) -> Path:
        filename = self.content.build_filename(self, pagearg)
        dir = self.content.src.contentpath[0]
        return prepare_output_path(self.site.outputdir, dir, filename)

    def add_depend(self, content: Content) -> None:
        self.depends.add(content.src.contentpath)

    def invalidate_cache(self) -> None:
        self._filename_cache = {}
        self._cache = defaultdict(dict)

    def get_cache(self, cachename: str, content: Content) -> Any:
        return self._cache[cachename].get(content.src.contentpath, None)

    def set_cache(self, cachename: str, content: Content, value: Any) -> None:
        self._cache[cachename][content.src.contentpath] = value

    def get_filename_cache(
        self, content: Content, tp_pagearg: Tuple[Any, ...]
    ) -> Union[str, None]:
        return self._filename_cache.get((content.src.contentpath, tp_pagearg), None)

    def set_filename_cache(
        self, content: Content, tp_pagearg: Tuple[Any, ...], filename: str
    ) -> None:
        self._filename_cache[(content.src.contentpath, tp_pagearg)] = filename

    @abstractmethod
    def build(self) -> Sequence[Path]:
        pass

    def _build_pagearg(self) -> Dict[Any, Any]:
        return {}

    def path_to(
        self,
        target: Content,
        pageargs: Dict[Any, Any],
        *,
        fragment: Optional[str] = None,
        abs_path: Optional[bool] = None,
    ) -> str:
        fragment = f"#{markupsafe.escape(fragment)}" if fragment else ""

        target_url = target.build_url(self, pageargs)
        if abs_path or self.content.use_abs_path:
            return target_url + fragment

        target_parsed = urllib.parse.urlsplit(target_url)
        page_url_parsed = urllib.parse.urlsplit(
            self.content.build_url(self, self._build_pagearg())
        )

        # return abs url if protocol or server differs
        if (target_parsed.scheme != page_url_parsed.scheme) or (
            target_parsed.netloc != page_url_parsed.netloc
        ):
            return target_url + fragment

        page_dir = posixpath.dirname(page_url_parsed.path)
        if page_dir == target_parsed.path:
            ret_path = page_dir
        else:
            ret_path = posixpath.relpath(target_parsed.path, page_dir)

        if target_parsed.path.endswith("/") and (not ret_path.endswith("/")):
            ret_path = ret_path + "/"
        return ret_path + fragment

    def link_to(
        self,
        target: Content,
        pageargs: Dict[Any, Any],
        *,
        text: Optional[str] = None,
        fragment: Optional[str] = None,
        search: Optional[str] = None,
        abs_path: bool = False,
        attrs: Optional[Dict[str, Any]] = None,
    ) -> str:

        if search:
            fragment = target.search_header(self, search)
            if fragment is None:
                raise ValueError(f"Cannot find text: {search}")

        if text is None:
            if fragment:
                text = target.get_headertext(self, fragment)
                if text is None:
                    raise ValueError(f"Cannot find fragment: {fragment}")

            if not text:
                text = markupsafe.escape(target.build_title(self))

        else:
            text = markupsafe.escape(text or "")

        s_attrs = []
        if attrs:
            for k, v in attrs.items():
                s_attrs.append(f"{markupsafe.escape(k)}='{markupsafe.escape(v)}'")
        path = markupsafe.escape(
            self.path_to(target, pageargs, fragment=fragment, abs_path=abs_path,)
        )
        return markupsafe.Markup(f"<a href='{path}' { ' '.join(s_attrs) }>{text}</a>")


class BinaryOutput(OutputContext):
    def write_body(self, outpath: Path) -> None:
        body = self.content.body
        if body is None:
            package = self.content.src.package
            if package:
                bytes = self.content.src.read_bytes()
                outpath.write_bytes(bytes)
            else:
                assert self.content.src.srcpath
                shutil.copyfile(self.content.src.srcpath, outpath)
        else:
            outpath.write_bytes(body)

    def build(self) -> Sequence[Path]:
        outfilename = self._get_outfilename({})
        self.write_body(outfilename)
        return [outfilename]


class JinjaOutput(OutputContext):
    content: Article

    def build(self) -> Sequence[Path]:
        templatename = self.content.get_metadata(self.site, "article_template")
        pagearg = self._build_pagearg()
        output = eval_jinja_template(self, self.content, templatename, pagearg)

        outfilename = self._get_outfilename({})
        outfilename.write_text(output)
        return [outfilename]


class IndexOutput(OutputContext):
    content: IndexPage
    value: str
    items: Sequence[Content]
    cur_page: int
    num_pages: int

    def __init__(
        self,
        site: Site,
        jinjaenv: Environment,
        contentpath: ContentPath,
        value: str,
        items: Sequence[Content],
        cur_page: int,
        num_pages: int,
    ) -> None:
        super().__init__(site, jinjaenv, contentpath)

        self.value = value
        self.items = items
        self.cur_page = cur_page
        self.num_pages = num_pages

    def _build_pagearg(self) -> Dict[Any, Any]:
        pagearg = {
            "group_value": self.value,
            "cur_page": self.cur_page,
            "num_pages": self.num_pages,
            "is_last": self.num_pages == self.cur_page,
            "articles": [ContentProxy(self, item) for item in self.items],
            "groupby": self.content.get_metadata(self.site, "groupby", None),
        }
        return pagearg

    def _get_templatename(self) -> str:
        if self.cur_page == 1:
            return cast(str, self.content.get_metadata(self.site, "indexpage_template"))
        template2 = self.content.get_metadata(self.site, "indexpage_template2", None)
        if template2:
            return cast(str, template2)
        else:
            return cast(str, self.content.get_metadata(self.site, "indexpage_template"))

    def build(self) -> Sequence[Path]:
        templatename = self._get_templatename()

        pagearg = self._build_pagearg()
        output = eval_jinja_template(self, self.content, templatename, pagearg)

        outfilename = self._get_outfilename(pagearg)
        outfilename.write_text(output)
        return [outfilename]


# from https://github.com/getpelican/feedgenerator
def get_tag_uri(url: str, date: datetime.datetime) -> str:
    """
    Creates a TagURI.
    See http://web.archive.org/web/20110514113830/http://diveintomark.org/archives/2004/05/28/howto-atom-id
    """
    bits = urlparse(url)
    d = ""
    if date is not None:
        d = ",%s" % datetime_safe.new_datetime(date).strftime("%Y-%m-%d %H:%M:%S.%f")
    fragment = ""
    if bits.fragment != "":
        fragment = "/%s" % (bits.fragment)
    return "tag:%s%s:%s%s" % (bits.hostname, d, bits.path, fragment)


class FeedOutput(OutputContext):
    content: FeedPage

    def build(self) -> Sequence[Path]:
        num_articles = int(self.content.get_metadata(self.site, "feed_num_articles"))

        filters = self.content.get_metadata(self.site, "filters", {}).copy()
        if "type" not in filters:
            filters["type"] = {"article"}

        if "draft" not in filters:
            filters["draft"] = {False}

        excludes = self.content.get_metadata(self.site, "excludes", {}).copy()

        dirnames = self.content.get_metadata(self.site, "directories", [])
        if dirnames:
            dirs: Optional[List[PathTuple]] = [
                parse_dir(d, self.content.src.contentpath[0]) for d in dirnames
            ]
        else:
            dirs = None

        contents = [
            c
            for c in self.site.files.get_contents(
                self.site, filters=filters, excludes=excludes, subdirs=dirs,
            )
        ][:num_articles]

        feedtype = self.content.get_metadata(self.site, "feedtype")
        if feedtype == "atom":
            cls = Atom1Feed
        elif feedtype == "rss":
            cls = Rss201rev2Feed
        else:
            raise ValueError(f"Invarid feed type: {feedtype}")

        feed = cls(
            title=self.content.get_metadata(self.site, "site_title"),
            link=self.content.get_metadata(self.site, "site_url"),
            feed_url=self.content.build_url(self, {}),
            description="",
        )

        for c in contents:
            link = c.build_url(self, {})
            description = c.build_abstract(self)
            date = c.get_metadata(self.site, "date")
            if date:
                feed.add_item(
                    title=c.build_title(self),
                    link=link,
                    unique_id=get_tag_uri(link, date),
                    description=str(description),
                    pubdate=date,
                )

        body = feed.writeString("utf-8")

        outfilename = self._get_outfilename({})
        outfilename.write_text(body)

        return [outfilename]


CONTEXTS: Dict[str, Type[OutputContext]] = {
    "binary": BinaryOutput,
    "article": JinjaOutput,
    "index": IndexOutput,
    "feed": FeedOutput,
}
