from typing import Tuple, List, Iterator, Set, Dict, Sequence, Optional
import os
import pickle
from pathlib import Path
from collections import defaultdict
from miyadaiku import CONFIG_FILE, MODULES_DIR, TEMPLATES_DIR, ContentPath, ContentSrc
from miyadaiku import site
from miyadaiku.context import OutputContext

DEP_FILE = "_depends.pickle"
DEP_VER = "2.0.0"


def is_newer(path: Path, mtime: float) -> bool:
    if not path.exists():
        return False
    return path.stat().st_mtime > mtime


def check_directory(path: Path, mtime: float) -> Iterator[Path]:
    if not path.exists():
        return

    for root, dirs, files in os.walk(path):
        rootpath = Path(root)
        for file in files:
            srcfile = rootpath / file
            if is_newer(srcfile, mtime):
                yield srcfile


Depends = Dict[ContentPath, Tuple[ContentSrc, Set[ContentPath]]]


def check_depends(site: site.Site) -> Tuple[bool, Optional[Set[ContentPath]]]:
    deppath = site.root / DEP_FILE

    mtime: float
    ver: str
    depends: Depends
    # load depends file
    try:
        with open(deppath, "rb") as f:
            mtime, ver, depends = pickle.load(f)

        if ver != DEP_VER:
            # old file format
            return True, None
    except Exception:
        # file load error
        return True, None

    # rebuild if config file updated
    if is_newer(site.root / CONFIG_FILE, mtime):
        return True, None

    # todo: check for removal of templates

    # check modules directory
    if any(check_directory(site.root / MODULES_DIR, mtime)):
        return True, set()

    # check template directory
    if any(check_directory(site.root / TEMPLATES_DIR, mtime)):
        return True, None

    # rebuild if contents are created or removed
    contentpaths = site.files.get_contentfiles_keys()
    if contentpaths != depends.keys():
        return True, None

    # select for updated files
    updated: Set[ContentPath] = set()

    for path in contentpaths:
        src = site.files.get_content(path).src

        # rebuild if metadata changed
        if src.metadata != depends[path][0].metadata:
            return True, None

        if (src.mtime or 0) > mtime:
            updated.update(depends[path][1])
    return False, updated


def save_deps(
    site: site.Site, deps: Sequence[Tuple[ContentSrc, Set[ContentPath]]]
) -> None:
    result: Depends = {}

    for contentpath, content in site.files.items():
        result[contentpath] = (content.src, set())

    for contentsrc, depends in deps:
        for dep_contentpath in depends:
            if dep_contentpath in result:
                result[dep_contentpath][1].add(contentsrc.contentpath)

    with open(site.root / DEP_FILE, "wb") as f:
        pickle.dump((site.files.mtime, DEP_VER, result), f)
