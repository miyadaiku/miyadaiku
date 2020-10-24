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
    NBCONVERT_TEMPLATES_DIR,
    TEMPLATES_DIR,
    BuildResult,
    ContentPath,
    DependsDict,
    OutputInfo,
)

if TYPE_CHECKING:
    from miyadaiku import site

DEP_FILE = "_depends.pickle"
DEP_VER = "4.0.0"


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


def check_depends(
    site: site.Site,
) -> Tuple[bool, Set[ContentPath], DependsDict, Sequence[OutputInfo]]:
    deppath = site.root / DEP_FILE

    mtime: float
    ver: str
    depends: DependsDict
    results: BuildResult

    # load depends file
    try:
        with open(deppath, "rb") as f:
            recs = pickle.load(f)

        if recs[1] != DEP_VER:
            # old file format
            return True, set(), {}, []

        mtime, ver, depends, outputinfos, errors = recs
    except Exception:
        # file load error
        return True, set(), {}, []

    # rebuild if config file updated
    if is_newer(site.root / CONFIG_FILE, mtime):
        return True, set(), {}, []

    # todo: check for removal of templates

    # check modules directory
    if any(check_directory(site.root / MODULES_DIR, mtime)):
        return True, set(), {}, []

    # check template directory
    if any(check_directory(site.root / TEMPLATES_DIR, mtime)):
        return True, set(), {}, []

    # check nbconvert template directory
    if any(check_directory(site.root / NBCONVERT_TEMPLATES_DIR, mtime)):
        return True, set(), {}, []

    def is_yaml(filename: Path) -> bool:
        return filename.suffix in (".yml", ".yaml")

    # check contents directory
    if any(check_directory(site.root / CONTENTS_DIR, mtime, is_yaml)):
        return True, set(), {}, []

    # rebuild if contents are created or removed
    contentpaths = site.files.get_contentfiles_keys()
    if contentpaths != depends.keys():
        return True, set(), {}, []

    # select for updated files
    updated: Set[ContentPath] = set()

    for path in contentpaths:
        src = site.files.get_content(path).src

        # rebuild if metadata changed
        if src.metadata != depends[path][0].metadata:
            return True, set(), {}, []

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

    outputinfos = [oi for oi in outputinfos if site.files.has_content(oi.contentpath)]
    return False, updated, depends, outputinfos


def update_deps(
    site: site.Site,
    d: DependsDict,
    results: BuildResult,
    errors: Set[ContentPath],
) -> DependsDict:

    new: Dict[ContentPath, Tuple[Set[ContentPath], Set[str]]] = {}

    for contentpath in site.files.get_contentfiles_keys():
        new[contentpath] = (set(), set())

    for contentpath, (contentsrc, depends, filenames) in d.items():
        new[contentpath] = (depends, {str(site.outputdir / f) for f in filenames})

    for contentsrc, depends, outputinfos in results:
        filenames = {str(oi.filename) for oi in outputinfos}
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


def update_outputinfos(
    site: site.Site, outputinfos: Sequence[OutputInfo], newresults: BuildResult
) -> Sequence[OutputInfo]:

    merged_outputs = {}
    for oi in outputinfos:
        if site.files.has_content(oi.contentpath):
            merged_outputs[oi.url] = oi

    for resultrec in newresults:
        for oi in resultrec[2]:
            merged_outputs[oi.url] = oi

    return list(merged_outputs.values())


def save_deps(
    site: site.Site,
    depsdict: DependsDict,
    outputinfos: Sequence[OutputInfo],
    errors: Set[ContentPath],
) -> None:

    with open(site.root / DEP_FILE, "wb") as f:
        pickle.dump((site.files.mtime, DEP_VER, depsdict, outputinfos, errors), f)
