from __future__ import annotations


from typing import (
    TYPE_CHECKING,
    Optional,
    NamedTuple,
    Type,
    Sequence,
    Tuple,
    Dict,
    Union,
    Any,
    Set,
    List,
    Callable,
)

from abc import abstractmethod
import os, time, random, shutil
from pathlib import Path
from functools import update_wrapper
import markupsafe

from miyadaiku import ContentPath, PathTuple, parse_path

if TYPE_CHECKING:
    from .contents import Content, Article, IndexPage
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
    def __init__(self, ctx: OutputContext, content: Content):
        self.context = ctx
        self.content = content

    def __getattr__(self, name: str) -> Any:
        return self.content.get_metadata(self.context.site, name)

    @safe_prop
    def contentpath(self) -> ContentPath:
        return self.content.src.contentpath

    @safe_prop
    def filename(self) -> str:
        return self.content.build_filename(self.context)

    @safe_prop
    def abstract(self) -> Union[None, str]:
        ret = self.content.build_abstract(self.context)
        return to_markupsafe(ret)

    @safe_prop
    def html(self) -> Union[None, str]:
        ret = self.content.build_html(self.context)
        return to_markupsafe(ret)

    @safe_prop
    def url(self) -> str:
        return self.content.build_url(self.context)

    @safe_prop
    def output_path(self) -> str:
        return self.content.build_output_path(self.context)

    def _load(self, target: str) -> Content:
        assert isinstance(target, str)
        path = parse_path(target, self.content.src.contentpath[0])
        return self.context.site.files.get_content(path)

    def load(self, target: str) -> ContentProxy:
        return ContentProxy(self.context, self._load(target))

    def _to_content(self, content: Union[ContentProxy, Content, str]) -> Content:
        if isinstance(content, str):
            return self._load(content)
        elif isinstance(content, ContentProxy):
            return content.content
        else:
            return content

    def path(
        self,
        target: Union[ContentProxy, Content, str],
        *,
        fragment: Optional[str] = None,
        abs_path: Optional[bool] = None,
        values: Optional[Any] = None,
        npage: Optional[int] = None,
    ) -> str:
        return self.context.content.path_to(
            self.context,
            self.content,
            fragment=fragment,
            abs_path=abs_path,
            values=values,
            npage=npage,
        )

    def path_to(
        self,
        target: Union[ContentProxy, Content, str],
        *,
        fragment: Optional[str] = None,
        abs_path: Optional[bool] = None,
        values: Optional[Any] = None,
        npage: Optional[int] = None,
    ) -> str:

        target_content = self._to_content(target)
        return self.context.content.path_to(
            self.context,
            target_content,
            fragment=fragment,
            abs_path=abs_path,
            values=values,
            npage=npage,
        )

    #
    #    def link(self, *args, **kwargs):
    #        return self.context.page_content.link_to(self.context, self, *args, **kwargs)
    #
    #
    def link_to(
        self,
        target: Union[ContentProxy, Content, str],
        *,
        text: Optional[str] = None,
        fragment: Optional[str] = None,
        abs_path: bool = False,
        attrs: Optional[Dict[str, Any]] = None,
        plain: bool = True,
        values: Optional[Any] = None,
        npage: Optional[int] = None,
    ) -> str:

        target_content = self._to_content(target)
        return self.context.content.link_to(
            self.context,
            target_content,
            text=text,
            fragment=fragment,
            abs_path=abs_path,
            attrs=attrs,
            plain=plain,
            values=values,
            npage=npage,
        )


#
#    def _to_markupsafe(self, s):
#        if not hasattr(s, "__html__"):
#            s = HTMLValue(s)
#        return s
#
#    @property
#    def abstract(self):
#        ret = self.__getattr__("abstract")
#        return self._to_markupsafe(ret)


class ConfigProxy:
    def __init__(self, ctx: "OutputContext"):
        self.context = ctx


class ContentsProxy:
    def __init__(self, ctx: "OutputContext"):
        self.context = ctx


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

    return Path(dest)


def eval_jinja(
    ctx: OutputContext,
    content: Content,
    propname: str,
    text: str,
    kwargs: Dict[str, Any],
) -> str:
    args = content.get_jinja_vars(ctx, content)
    args.update(kwargs)
    template = ctx.site.jinjaenv.from_string(text)
    template.filename = f"{content.repr_filename()}#{propname}"
    return template.render(**kwargs)


def eval_jinja_template(ctx: OutputContext, content: Content, templatename: str) -> str:
    template = ctx.site.jinjaenv.get_template(templatename)
    template.filename = templatename

    kwargs = content.get_jinja_vars(ctx, content)
    return template.render(**kwargs)


class HTMLIDInfo(NamedTuple):
    id: str
    tag: str
    text: str


class HTMLInfo(NamedTuple):
    html: str
    headers: List[HTMLIDInfo]
    header_anchors: List[HTMLIDInfo]
    fragments: List[HTMLIDInfo]


class OutputContext:
    site: Site
    contentpath: ContentPath
    content: Content
    _html_cache: Dict[ContentPath, HTMLInfo]
    _filename_cache: Dict[ContentPath, str]
    depends: Set[ContentPath]

    def __init__(self, site: Site, contentpath: ContentPath) -> None:
        self.site = site
        self.contentpath = contentpath
        self.content = site.files.get_content(self.contentpath)
        self.depends = set()
        self._html_cache = {}
        self._filename_cache = {}

    def get_outfilename(self) -> Path:
        # todo: get metadata
        dir, file = self.content.src.contentpath
        return prepare_output_path(self.site.outputdir, dir, file)

    def add_depend(self, content: Content) -> None:
        self.depends.add(content.src.contentpath)

    def get_html_cache(self, content: Content) -> Union[HTMLInfo, None]:
        return self._html_cache.get(content.src.contentpath, None)

    def set_html_cache(self, content: Content, info: HTMLInfo) -> None:
        self._html_cache[content.src.contentpath] = info

    def get_filename_cache(self, content: Content) -> Union[str, None]:
        return self._filename_cache.get(content.src.contentpath, None)

    def set_filename_cache(self, content: Content, filename: str) -> None:
        self._filename_cache[content.src.contentpath] = filename

    @abstractmethod
    def build(self) -> Tuple[Sequence[Path], Sequence[ContentPath]]:
        pass


class BinaryOutput(OutputContext):
    def write_body(self, outpath: Path) -> None:
        body = self.content.body
        if body is None:
            package = self.content.src.package
            if package:
                bytes = self.content.src.read_bytes()
                outpath.write_bytes(bytes)
            else:
                shutil.copyfile(self.content.src.srcpath, outpath)
        else:
            outpath.write_text(body)

    def build(self) -> Tuple[Sequence[Path], Sequence[ContentPath]]:
        outfilename = self.get_outfilename()
        self.write_body(outfilename)
        return [outfilename], [self.content.src.contentpath]


class JinjaOutput(OutputContext):
    content: Article

    def build(self) -> Tuple[Sequence[Path], Sequence[ContentPath]]:

        templatename = self.content.get_metadata(self.site, "article_template")
        output = eval_jinja_template(self, self.content, templatename)

        outfilename = self.get_outfilename()
        outfilename.write_text(output)
        return [outfilename], [self.content.src.contentpath]


class IndexOutput(OutputContext):
    content: IndexPage
    names: Tuple[str, ...]
    items: Sequence[Content]
    cur_page: int
    num_pages: int

    def __init__(
        self,
        site: Site,
        contentpath: ContentPath,
        names: Tuple[str, ...],
        items: Sequence[Content],
        cur_page: int,
        num_pages: int,
    ) -> None:
        super().__init__(site, contentpath)

        self.names = names
        self.items = items
        self.cur_page = cur_page
        self.num_pages = num_pages

    def build(self) -> Tuple[Sequence[Path], Sequence[ContentPath]]:
        return [], []


CONTEXTS: Dict[str, Type[OutputContext]] = {
    "binary": BinaryOutput,
    "article": JinjaOutput,
    "index": IndexOutput,
}
