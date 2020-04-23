from __future__ import annotations


from typing import TYPE_CHECKING, Any, List, Type, Sequence, Dict, Union, Tuple, Set
import multiprocessing
import pickle
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import tempfile

from jinja2 import Environment

from miyadaiku import ContentPath, PathTuple, ContentSrc, repr_contentpath

from . import context, log

if TYPE_CHECKING:
    from .contents import Content
    from .site import Site


global logger
logger = logging.getLogger(__name__)


class Builder:
    contentpath: ContentPath

    @classmethod
    def create_builders(cls, site: Site, content: Content) -> List[Builder]:
        return [cls(content)]

    def __init__(self, content: Content) -> None:
        self.contentpath = content.src.contentpath

    def build_context(self, site: Site, jinjaenv: Environment) -> context.OutputContext:
        content = site.files.get_content(self.contentpath)
        contexttype = context.CONTEXTS.get(
            content.src.metadata["type"], context.BinaryOutput
        )
        return contexttype(site, jinjaenv, self.contentpath)


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

    def build_context(self, site: Site, jinjaenv: Environment) -> context.OutputContext:
        items = [site.files.get_content(path) for path in self.items]
        return context.IndexOutput(
            site,
            jinjaenv,
            self.contentpath,
            self.value,
            items,
            self.cur_page,
            self.num_pages,
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


MIN_BATCH_SIZE = 10


def split_batch(builders: Sequence[Any]) -> Sequence[Any]:
    num = len(builders)
    max_batches = (num // MIN_BATCH_SIZE) or 1
    batch_count = min(max_batches, multiprocessing.cpu_count())
    batches: List[List[Builder]] = [[] for _ in range(batch_count)]

    for i, builder in enumerate(builders):
        batches[i % batch_count].append(builder)

    return batches


def build_batch(
    site: Site, jinjaev: Environment, builders: List[Builder]
) -> List[Tuple[ContentSrc, Set[ContentPath]]]:
    ret: List[Tuple[ContentSrc, Set[ContentPath]]] = []

    for builder in builders:
        try:
            context = builder.build_context(site, jinjaev)
            logger.info("Building %s", context.content.src.repr_filename())
            context.build()

            ret.append((context.content.src, set(context.depends)))
        except:
            logger.exception(
                "Error while building %s", repr_contentpath(builder.contentpath)
            )

    return ret


def mp_build_batch(queue: Any, picklefile: str, builders: List[Builder]) -> None:
    try:
        site = pickle.load(open(picklefile, "rb"))

        jinjaenv = site.build_jinjaenv()
        site.load_modules()

        ret = build_batch(site, jinjaenv, builders)
        queue.put(("DEPENDS", ret))
    except:
        logger.exception("Error in builder process:")

    finally:
        queue.put(None)
        queue.close()
        queue.join_thread()


def run_build(picklefile: str, batch: List[Builder]) -> List[Tuple[str, Any]]:
    queue: Any = multiprocessing.Queue()
    p = multiprocessing.Process(target=mp_build_batch, args=(queue, picklefile, batch))
    p.start()

    msgs = []
    while True:
        msg = queue.get()
        if msg is None:
            break
        if msg[0] == "LOG":
            print(msg)
        elif msg[0] == "DEPENDS":
            msgs.append(msg)

    queue.close()
    queue.join_thread()

    p.join()
    return msgs


async def submit(
    site: Site, batches: Sequence[List[Builder]]
) -> List[Tuple[ContentSrc, Set[ContentPath]]]:
    fd, picklefile = tempfile.mkstemp()
    try:
        sitestr = pickle.dumps(site)
        os.write(fd, sitestr)
        os.close(fd)
        fd = 0

        loop = asyncio.get_running_loop()
        futs = []
        deps = []

        executor = ThreadPoolExecutor(max_workers=len(batches))
        for batch in batches:
            futs.append(loop.run_in_executor(executor, run_build, picklefile, batch))

        for fut in futs:
            msgs = await fut
            for msg in msgs:
                if msg[0] == "DEPENDS":
                    deps.extend(msg[1])

        return deps

    finally:
        if fd:
            os.close(fd)
        os.unlink(picklefile)


def submit_debug(
    site: Site, batches: Sequence[List[Builder]]
) -> List[Tuple[ContentSrc, Set[ContentPath]]]:
    jinjaenv = site.build_jinjaenv()
    site.load_modules()
    ret = []

    for batch in batches:
        deps = build_batch(site, jinjaenv, batch)
        ret.extend(deps)
    return ret


def build(site: Site) -> Sequence[Tuple[ContentSrc, Set[ContentPath]]]:
    contents = [content for contentpath, content in site.files.items()]
    builders = []
    for contentpath, content in site.files.items():
        builders.extend(create_builders(site, content))

    batches = split_batch(builders)

    if not site.outputdir.is_dir():
        site.outputdir.mkdir(parents=True, exist_ok=True)

    ret = asyncio.run(submit(site, batches))
    #    ret = submit_debug(site, batches)
    return ret
