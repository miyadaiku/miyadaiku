from __future__ import annotations


from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Type,
    Sequence,
    Dict,
    Union,
    Tuple,
    Set
)
import multiprocessing
import pickle
import asyncio

from miyadaiku import ContentPath, PathTuple, ContentSrc

from .context import CONTEXTS, OutputContext, BinaryOutput, IndexOutput

if TYPE_CHECKING:
    from .contents import Content
    from .site import Site


class Builder:
    contentpath: ContentPath

    @classmethod
    def create_builders(cls, site: Site, content: Content) -> List[Builder]:
        return [cls(content)]

    def __init__(self, content: Content) -> None:
        self.contentpath = content.src.contentpath

    def build_context(self, site: Site) -> OutputContext:
        content = site.files.get_content(self.contentpath)
        contexttype = CONTEXTS.get(content.src.metadata["type"], BinaryOutput)
        return contexttype(site, self.contentpath)


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
    value: str
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

        for values, group in groups:
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

                if values:
                    value = values[0]
                else:
                    value = ""

                ret.append(cls(content, value, articles, page + 1, num_pages))

        return ret

    def build_context(self, site: Site) -> OutputContext:
        items = [site.files.get_content(path) for path in self.items]
        return IndexOutput(
            site, self.contentpath, self.value, items, self.cur_page, self.num_pages
        )

    def __init__(
        self,
        content: Content,
        value: str,
        items: Sequence[Content],
        cur_page: int,
        num_pages: int,
    ) -> None:
        super().__init__(content)

        self.items = [c.src.contentpath for c in items]
        self.value = value
        self.cur_page = cur_page
        self.num_pages = num_pages


BUILDERS: Dict[str, Type[Builder]] = {
    "binary": Builder,
    "article": Builder,
    "index": IndexBuilder,
    "feed": Builder,
}


def create_builders(site: Site, content: Content) -> List[Builder]:
    buildercls = BUILDERS.get(content.src.metadata["type"], None)
    if buildercls:
        return buildercls.create_builders(site, content)
    else:
        return []


def split_batch(builders:Sequence[Any])->Sequence[Any]:
    num = len(builders)
    batch_count = min(num, multiprocessing.cpu_count())

    batchsize, remainder = divmod(num, batch_count)
    batches = []

    for i in range(0, remainder):
        batches.append(builders[i*(batchsize+1):(i+1)*(batchsize+1)])

    start = (batchsize+1)*remainder
    for i in range(0, batch_count-remainder):
        batches.append(builders[start+ i*batchsize:start+(i+1)*batchsize])

    return batches


def build_batch(queue:Any, site:Site, builders:List[Builder])->List[OutputContext]:
    contexts:List[OutputContext] = []

    try:

        for builder in builders:
            context = builder.build_context(site)
            queue.put(f"Building {context.content.src.repr_filename()}")
            context.build()
            contexts.append(context)

    finally:
        queue.put(None)
        queue.close()

    return contexts


def run_build_batch(queue:Any, site_pickle:bytes, builders:List[Builder])->List[OutputContext]:
    site = pickle.loads(site_pickle)
    site.build_jinjaenv()

    return build_batch(queue, site, builders)




async def submit(site:Site, batches: Sequence[List[Builder]])->None:
        for batch in batches:
            queue: Any = multiprocessing.Queue()
        ret = build_batch(queue, site, batch)


def build(site: Site)->Sequence[Tuple[ContentSrc, Set[ContentPath]]]:
    contents = [content for contentpath, content in site.files.items()]
    builders = []
    for contentpath, content in site.files.items():
        builders.extend(create_builders(site, content))

    batches = split_batch(builders)

    if not site.outputdir.is_dir():
        site.outputdir.mkdir(parents=True, exist_ok=True)



    asyncio.run(submit(site, batches))

    try:
        ret:List[Tuple[ContentSrc, Set[ContentPath]]] = []

        for batch in batches:
            queue: Any = multiprocessing.Queue()
            contexts = build_batch(queue, site, batch)

            for context in contexts:
                ret.append((context.content.src, set(context.depends)))
    finally:
        queue.close()
        queue.join_thread()
        queue = None

    

    return ret

#
#
#    site.build_jinjaenv()
#
#    builders = []
#    for contentpath, content in site.files.items():
#        builders.extend(create_builders(site, content))
#
#    if not site.outputdir.is_dir():
#        site.outputdir.mkdir(parents=True, exist_ok=True)
#
#    contexts = []
#    for builder in builders:
#        context = builder.build_context(site)
#        context.build()
#        contexts.append(context)
#
#    return contexts
#    

