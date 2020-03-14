from typing import List, Iterator, Dict, Tuple, Optional, DefaultDict, Any, Callable, Set, Union
import os
import fnmatch
import pkg_resources
from pathlib import Path, PurePosixPath, PurePath
import logging

import miyadaiku

logger = logging.getLogger(__name__)



def is_ignored(ignores:Set[str], name:str):
    if name.lower().endswith(miyadaiku.METADATA_FILE_SUFFIX):
        return True

    for p in ignores:
        if fnmatch.fnmatch(name, p):
            return True

PATHTUPLE = Tuple[str, ...]

def to_pathtuple(path)->PATHTUPLE:
    if isinstance(path, tuple):
        return path
    spath = str(path)
    spath = spath.replace("\\", "/").strip("/")
    ret = tuple(path.split("/"))
    for c in ret:
        if set(c.strip()) == '.':
            raise ValueError("Invalid path: {path}")
    return ret

def walk_directory(path:Path, ignores:Set[str])->Iterator[Tuple[str, PATHTUPLE]]:
    logger.info(f"Loading {path}")
    path = path.expanduser().resolve()
    if not path.is_dir():
        logger.debug(f'directory: {str(path)} is not a valid directory.')
        return

    pathlen = len(str(path)) + 1

    for root, dirs, files in os.walk(path):
        rootpath = Path(root)
        if rootpath.stem.startswith('.'):
            continue

        dirs[:] = (dirname for dirname in dirs if not is_ignored(ignores, dirname))
        filenames = (filename for filename in files if not is_ignored(ignores, filename))

        for name in filenames:
            filename = str(rootpath / name)
            yield (filename, to_pathtuple(filename[pathlen:]))


def _iter_package_files(package:str, path:str, ignores:Set[str])->Iterator[str]:
    children = pkg_resources.resource_listdir(package, path)
    for child in children:
        if is_ignored(ignores, child):
            continue

        p = f'{path}{child}'
        if pkg_resources.resource_isdir(package, p):
            yield from _iter_package_files(package, p+"/", ignores)
        else:
            yield p


def walk_package(package:str, path:str, ignores:Set[str])->Iterator[Tuple[str, PATHTUPLE]]:
    logger.info(f"Loading {package}/{path}")

    if not path.endswith('/'):
        path = path + "/"
    pathlen = len(path)

    if not pkg_resources.resource_isdir(package, path):
        logger.debug(f'directory: {path} is not a valid directory.')
        return

    for filename in _iter_package_files(package, path, ignores):
        destname = filename[pathlen:]
        yield filename, to_pathtuple(destname)
