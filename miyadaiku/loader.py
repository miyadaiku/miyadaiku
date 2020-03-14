from typing import List, Iterator, Dict, Tuple, Optional, DefaultDict, Any, Callable, Set, Union, TypedDict
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

PathTuple = Tuple[str, ...]

def to_pathtuple(path)->PathTuple:
    if isinstance(path, tuple):
        return path
    spath = str(path)
    spath = spath.replace("\\", "/").strip("/")
    ret = tuple(path.split("/"))
    for c in ret:
        if set(c.strip()) == '.':
            raise ValueError("Invalid path: {path}")
    return ret


class FileContent(TypedDict, total=False):
    srcpath: Path
    destpath: PathTuple


class ThemeContent(TypedDict, total=False):
    package: str
    srcpath: str
    destpath: PathTuple
    

def walk_directory(path:Path, ignores:Set[str])->Iterator[FileContent]:
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
            filename = rootpath / name
            yield {'srcpath': filename, 'destpath': to_pathtuple(str(filename)[pathlen:])}


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


def walk_package(package:str, path:str, ignores:Set[str])->Iterator[ThemeContent]:
    logger.info(f"Loading {package}/{path}")

    if not path.endswith('/'):
        path = path + "/"
    pathlen = len(path)

    if not pkg_resources.resource_isdir(package, path):
        logger.debug(f'directory: {path} is not a valid directory.')
        return

    for filename in _iter_package_files(package, path, ignores):
        destname = filename[pathlen:]
        yield {'package': package, 'srcpath': filename, 'destpath': to_pathtuple(destname), }
