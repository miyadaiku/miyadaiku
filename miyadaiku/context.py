from __future__ import annotations


from typing import (
    TYPE_CHECKING,
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

if TYPE_CHECKING:
    from .contents import Content
    from .site import Site
    from .builder import Builder


class ContentProxy:
    def __init__(self, site: Site, context: OutputContext, content: Content):
        self.site = site
        self.context = context
        self.content = content


#    def __getattr__(self, name: str) -> Any:
#        return self.content.get_metadata(self.site, name)
#
#    _omit = object()
#
#    def load(self, target:Content)->ContentProxy:
#        ret = self.content.get_content(target)
#        return ContentProxy(self.context, ret)
#
#    def path(self, *args, **kwargs):
#        return self.context.page_content.path_to(self, *args, **kwargs)
#
#    def link(self, *args, **kwargs):
#        return self.context.page_content.link_to(self.context, self, *args, **kwargs)
#
#    def path_to(self, target, *args, **kwargs):
#        target = self.load(target)
#        return self.context.page_content.path_to(target, *args, **kwargs)
#
#    def link_to(self, target, *args, **kwargs):
#        target = self.load(target)
#        return self.context.page_content.link_to(self.context, target, *args, **kwargs)
#
#    def _to_markupsafe(self, s):
#        if not hasattr(s, "__html__"):
#            s = HTMLValue(s)
#        return s
#
#    @property
#    def html(self):
#        ret = self.__getattr__("html")
#        return self._to_markupsafe(ret)
#
#    @property
#    def abstract(self):
#        ret = self.__getattr__("abstract")
#        return self._to_markupsafe(ret)


class ConfigProxy:
    def __init__(self, context: "OutputContext"):
        self.context = context


class ContentsProxy:
    def __init__(self, context: "OutputContext"):
        self.context = context


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


class OutputContext:
    site: Site
    builder: Builder
    contentpath: ContentPath
    content: Content
    _outputs: Dict[ContentPath, Union[None, bytes]]

    def __init__(self, site: Site, builder: Builder, contentpath: ContentPath) -> None:
        self.site = site
        self.builder = builder
        self.contentpath = contentpath
        self.content = site.files.get_content(self.contentpath)
        self._outputs = {}

    def get_outfilename(self) -> Path:
        dir, file = self.content.src.contentpath
        return prepare_output_path(self.site.outputdir, dir, file)

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


class HTMLOutput(OutputContext):
    def get_jinja_vars(self, site: Site, content: Content) -> Dict[str, Any]:

        ret = {}
        for name in content.get_metadata(site, "imports"):
            template = site.jinjaenv.get_template(name)
            fname = name.split("!", 1)[-1]
            modulename = PurePosixPath(fname).stem
            ret[modulename] = template.module

        ret["page"] = ContentProxy(site, self, site.files.get_content(self.contentpath))
        ret["content"] = ContentProxy(site, self, content)

        ret["contents"] = ContentsProxy(self)
        ret["config"] = ConfigProxy(self)

        return ret

    def build(self) -> Tuple[Sequence[Path], Sequence[ContentPath]]:

        templatename = self.content.get_metadata(self.site, "article_template")
        template = self.site.jinjaenv.get_template(templatename)
        template.filename = templatename

        kwargs = self.get_jinja_vars(self.site, self.content)
        output = template.render(**kwargs)

        outfilename = self.get_outfilename()
        outfilename.write_text(output)
        return [outfilename], [self.content.src.contentpath]


class IndexOutput(HTMLOutput):
    names: Tuple[str, ...]
    items: Sequence[Content]
    cur_page: int
    num_pages: int

    def __init__(
        self,
        site: Site,
        builder: Builder,
        contentpath: ContentPath,
        names: Tuple[str, ...],
        items: Sequence[Content],
        cur_page: int,
        num_pages: int,
    ) -> None:
        super().__init__(site, builder, contentpath)

        self.names = names
        self.items = items
        self.cur_page = cur_page
        self.num_pages = num_pages

    def build(self) -> Tuple[Sequence[Path], Sequence[ContentPath]]:
        return [], []


CONTEXTS: Dict[str, Type[OutputContext]] = {
    "binary": BinaryOutput,
    "article": HTMLOutput,
    "index": IndexOutput,
}
