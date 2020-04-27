from __future__ import annotations

from typing import Dict, Iterator, Sequence, Set, TYPE_CHECKING, Tuple
import os
import pickle
from pathlib import Path
from miyadaiku import (
    CONFIG_FILE,
    MODULES_DIR,
    TEMPLATES_DIR,
    ContentPath,
    ContentSrc,
    DependsDict,
)

if TYPE_CHECKING:
    from miyadaiku import site

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


def check_depends(site: site.Site) -> Tuple[bool, Set[ContentPath], DependsDict]:
    deppath = site.root / DEP_FILE

    mtime: float
    ver: str
    depends: DependsDict
    # load depends file
    try:
        with open(deppath, "rb") as f:
            mtime, ver, depends, errors = pickle.load(f)

        if ver != DEP_VER:
            # old file format
            return True, set(), {}
    except Exception:
        # file load error
        return True, set(), {}

    # rebuild if config file updated
    if is_newer(site.root / CONFIG_FILE, mtime):
        return True, set(), {}

    # todo: check for removal of templates

    # check modules directory
    if any(check_directory(site.root / MODULES_DIR, mtime)):
        return True, set(), {}

    # check template directory
    if any(check_directory(site.root / TEMPLATES_DIR, mtime)):
        return True, set(), {}

    # rebuild if contents are created or removed
    contentpaths = site.files.get_contentfiles_keys()
    if contentpaths != depends.keys():
        return True, set(), {}

    # select for updated files
    updated: Set[ContentPath] = set()

    for path in contentpaths:
        src = site.files.get_content(path).src

        # rebuild if metadata changed
        if src.metadata != depends[path][0].metadata:
            return True, set(), {}

        if ((src.mtime or 0) > mtime) or (path in errors):
            updated.update(depends[path][1])
            updated.add(path)

    return False, updated, depends


def update_deps(
    site: site.Site,
    d: DependsDict,
    deps: Sequence[Tuple[ContentSrc, Set[ContentPath]]],
    errors: Set[ContentPath],
) -> DependsDict:
    new: Dict[ContentPath, Set[ContentPath]] = {}

    for contentpath, (contentsrc, depends) in d.items():
        new[contentpath] = depends

    for contentsrc, depends in deps:
        for dep_contentpath in depends:
            if dep_contentpath in new:
                new[dep_contentpath].add(contentsrc.contentpath)
            else:
                new[dep_contentpath] = set([contentsrc.contentpath])

    ret: DependsDict = {}
    for contentpath, depends in new.items():
        if site.files.has_content(contentpath):
            src = site.files.get_content(contentpath).src
            ret[contentpath] = (src, depends)

    return ret


def save_deps(site: site.Site, depsdict: DependsDict, errors: Set[ContentPath]) -> None:

    #    for contentpath, content in site.files.items():
    #        result[contentpath] = (content.src, set())
    #
    #    for contentsrc, depends in deps:
    #        for dep_contentpath in depends:
    #            if dep_contentpath in result:
    #                result[dep_contentpath][1].add(contentsrc.contentpath)

    with open(site.root / DEP_FILE, "wb") as f:
        pickle.dump((site.files.mtime, DEP_VER, depsdict, errors), f)
