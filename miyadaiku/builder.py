from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import pickle
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

from jinja2 import Environment

from miyadaiku import (
    ContentPath,
    ContentSrc,
    DependsDict,
    PathTuple,
    parse_dir,
    repr_contentpath,
)

from . import context, depends, extend, mp_log

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

        if "type" not in filters:
            filters["type"] = {"article"}

        if "draft" not in filters:
            filters["draft"] = {False}

        excludes = content.get_metadata(site, "excludes", {}).copy()

        dirnames = content.get_metadata(site, "directories", [])
        if dirnames:
            dirs: Optional[List[PathTuple]] = [
                parse_dir(d, content.src.contentpath[0]) for d in dirnames
            ]
        else:
            dirs = None

        groupby = content.get_metadata(site, "groupby", None)
        groups = site.files.group_items(
            site,
            groupby,
            filters=filters,
            excludes=excludes,
            subdirs=dirs,
            recurse=True,
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

        if not groupby:
            if not ret:
                ret = [cls(content, "", [], 1, 1)]

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
) -> Tuple[
    int, int, List[Tuple[ContentSrc, Set[ContentPath], Set[str]]], Set[ContentPath]
]:

    ret: List[Tuple[ContentSrc, Set[ContentPath], Set[str]]] = []
    errors: Set[ContentPath] = set()

    ok = err = 0
    for builder in builders:
        try:
            new_context = builder.build_context(site, jinjaev)
            context = extend.run_pre_build(new_context)
            if not context:
                continue
            logger.info("Building %s", context.content.src.repr_filename())
            filenames = context.build()
            extend.run_post_build(context, filenames)

            ret.append(
                (
                    context.content.src,
                    set(context.depends),
                    set(str(f) for f in filenames),
                )
            )
            ok += 1

        except Exception:
            err += 1
            errors.add(builder.contentpath)
            logger.exception(
                "Error while building %s", repr_contentpath(builder.contentpath)
            )

    return ok, err, ret, errors


def mp_build_batch(queue: Any, picklefile: str, builders: List[Builder]) -> None:
    try:
        site = pickle.load(open(picklefile, "rb"))
        mp_log.init_mp_logging(queue)
        try:
            site.load_hooks()
            site.load_modules()
            jinjaenv = site.build_jinjaenv()

            ret = build_batch(site, jinjaenv, builders)
            queue.put(("RESULT", ret))
        except:  # NOQA
            logger.exception("Error in builder process:")
            raise

        finally:
            mp_log.flush_mp_logging()
            queue.put(None)
            queue.close()
            queue.join_thread()
    except:  # noqa
        traceback.print_exc()
        raise


def dispatch_log(msgs: List[Dict[str, Any]]) -> None:
    for msg in msgs:
        lv = msg["levelno"]
        logger.log(lv, msg["msg"], extra=dict(msgdict=msg))


def run_build(
    loop: asyncio.AbstractEventLoop, picklefile: str, batch: List[Builder]
) -> List[Tuple[str, Any]]:
    queue: Any = multiprocessing.Queue()
    p = multiprocessing.Process(target=mp_build_batch, args=(queue, picklefile, batch))
    p.start()

    msgs = []
    while True:
        msg = queue.get()
        if msg is None:
            break
        if msg[0] == "LOGS":
            loop.call_soon_threadsafe(dispatch_log, msg[1])

        elif msg[0] == "RESULT":
            msgs.append(msg)

    queue.close()
    queue.join_thread()

    p.join()
    return msgs


async def submit(
    site: Site, batches: Sequence[List[Builder]]
) -> Tuple[
    int, int, List[Tuple[ContentSrc, Set[ContentPath], Set[str]]], Set[ContentPath]
]:

    fd, picklefile = tempfile.mkstemp()

    try:
        sitestr = pickle.dumps(site)
        os.write(fd, sitestr)
        os.close(fd)
        fd = 0

        loop = asyncio.get_running_loop()
        futs = []
        deps = []
        errors = set()

        executor = ThreadPoolExecutor(max_workers=len(batches))
        for batch in batches:
            futs.append(
                loop.run_in_executor(executor, run_build, loop, picklefile, batch)
            )

        ok = err = 0
        for fut in futs:
            msgs = await fut
            for msg in msgs:
                if msg[0] == "RESULT":
                    _ok, _err, _deps, _errors = msg[1]
                    ok += _ok
                    err += _err
                    deps.extend(_deps)
                    errors.update(_errors)

        return ok, err, deps, errors

    finally:
        if fd:
            os.close(fd)
        os.unlink(picklefile)


def submit_debug(
    site: Site, batches: Sequence[List[Builder]]
) -> Tuple[
    int, int, List[Tuple[ContentSrc, Set[ContentPath], Set[str]]], Set[ContentPath]
]:

    site.load_modules()
    jinjaenv = site.build_jinjaenv()

    ok = err = 0
    ret = []
    errors = set()

    for batch in batches:
        _ok, _err, deps, _errors = build_batch(site, jinjaenv, batch)
        ok += _ok
        err += _err
        ret.extend(deps)
        errors.update(_errors)
    return ok, err, ret, errors


def build(site: Site) -> Tuple[int, int, DependsDict, Set[ContentPath]]:
    if site.rebuild:
        rebuild = True
    else:
        rebuild, updates, deps = depends.check_depends(site)

    builders = []
    for contentpath, content in site.files.items():
        if rebuild or (contentpath in updates):
            builders.extend(create_builders(site, content))

    batches = split_batch(builders)

    if not site.outputdir.is_dir():
        site.outputdir.mkdir(parents=True, exist_ok=True)

    if not site.debug:
        ok, err, newdeps, errors = asyncio.run(submit(site, batches))
    else:
        ok, err, newdeps, errors = submit_debug(site, batches)

    if rebuild:
        deps = {}

    deps = depends.update_deps(site, deps, newdeps, errors)

    depends.save_deps(site, deps, errors)
    return (ok, err, deps, errors)
