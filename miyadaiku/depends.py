from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Callable,
    Dict,
    Iterator,
    Optional,
    Sequence,
    Set,
    Tuple,
)

from miyadaiku import (
    CONFIG_FILE,
    CONTENTS_DIR,
    MODULES_DIR,
    TEMPLATES_DIR,
    ContentPath,
    ContentSrc,
    DependsDict,
)

if TYPE_CHECKING:
    from miyadaiku import site

DEP_FILE = "_depends.pickle"
DEP_VER = "3.0.0"


def is_newer(path: Path, mtime: float) -> bool:
    if not path.exists():
        return False
    return path.stat().st_mtime > mtime


def check_directory(
    path: Path, mtime: float, pred: Optional[Callable[[Path], bool]] = None
) -> Iterator[Path]:
    if not path.exists():
        return

    for root, dirs, files in os.walk(path):
        rootpath = Path(root)
        for file in files:
            srcfile = rootpath / file
            if pred and not pred(srcfile):
                continue
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

    def is_yaml(filename: Path) -> bool:
        return filename.suffix in (".yml", ".yaml")

    # check contents directory
    if any(check_directory(site.root / CONTENTS_DIR, mtime, is_yaml)):
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
            continue

        for filename in depends[path][2]:
            p = site.outputdir / filename
            if not p.exists():
                updated.add(path)
                break

            stat = p.stat()
            if (src.mtime or 0) > stat.st_mtime:
                updated.add(path)
                break

    return False, updated, depends


def update_deps(
    site: site.Site,
    d: DependsDict,
    deps: Sequence[Tuple[ContentSrc, Set[ContentPath], Set[str]]],
    errors: Set[ContentPath],
) -> DependsDict:

    new: Dict[ContentPath, Tuple[Set[ContentPath], Set[str]]] = {}

    for contentpath in site.files.get_contentfiles_keys():
        new[contentpath] = (set(), set())

    for contentpath, (contentsrc, depends, filenames) in d.items():
        new[contentpath] = (depends, {str(site.outputdir / f) for f in filenames})

    for contentsrc, depends, filenames in deps:
        if contentsrc.contentpath in new:
            new[contentsrc.contentpath][1].update(filenames)
        else:
            new[contentsrc.contentpath] = (set(), filenames)

        for dep_contentpath in depends:
            if dep_contentpath in new:
                new[dep_contentpath][0].add(contentsrc.contentpath)
            else:
                new[dep_contentpath] = (set([contentsrc.contentpath]), set())

    outputpath = str(site.outputdir)
    ret: DependsDict = {}
    for contentpath, (depends, filenames) in new.items():
        if site.files.has_content(contentpath):
            src = site.files.get_content(contentpath).src

            filenames = {os.path.relpath(f, outputpath) for f in filenames}
            ret[contentpath] = (src, depends, filenames)

    return ret


def save_deps(site: site.Site, depsdict: DependsDict, errors: Set[ContentPath]) -> None:

    with open(site.root / DEP_FILE, "wb") as f:
        pickle.dump((site.files.mtime, DEP_VER, depsdict, errors), f)
