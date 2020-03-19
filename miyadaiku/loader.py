from typing import List, Iterator, Dict, Tuple, Optional, DefaultDict, Any, Callable, Set, Union, TypedDict
import os
import fnmatch
import pkg_resources
from pathlib import Path, PurePosixPath, PurePath
import logging
import yaml

import miyadaiku
from miyadaiku import PathTuple
from . import rst, md

logger = logging.getLogger(__name__)



def is_ignored(ignores:Set[str], name:str):
    if name.lower().endswith(miyadaiku.METADATA_FILE_SUFFIX):
        return True

    for p in ignores:
        if fnmatch.fnmatch(name, p):
            return True

def to_pathtuple(path: str)->PathTuple:
    spath = str(path)
    spath = spath.replace("\\", "/").strip("/")
    ret = path.split("/")

    for c in ret:
        if set(c.strip()) == '.':
            raise ValueError("Invalid path: {path}")

    dir = tuple(ret[:-1])
    return (dir, ret[-1])


class FileContent(TypedDict, total=False):
    srcpath: Path
    contentpath: PathTuple


class ThemeContent(TypedDict, total=False):
    package: str
    srcpath: str
    contentpath: PathTuple
    

def walk_directory(path:Path, ignores:Set[str])->Iterator[FileContent]:
    logger.info(f"Loading {path}")
    path = path.expanduser().resolve()
    if not path.is_dir():
        logger.debug(f'directory: {str(path)} is not a valid directory.')
        return

    for root, dirs, files in os.walk(path):
        rootpath = Path(root)
        if rootpath.stem.startswith('.'):
            continue

        dirs[:] = (dirname for dirname in dirs if not is_ignored(ignores, dirname))
        filenames = (filename for filename in files if not is_ignored(ignores, filename))

        for name in filenames:
            filename = (rootpath / name).resolve()
            yield {'srcpath': filename, 'contentpath': to_pathtuple(str(filename.relative_to(path)))}

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
        yield {'package': package, 'srcpath': filename, 'contentpath': to_pathtuple(destname), }




FILELOADERS = {
    '.rst': rst.load,
    '.rest': rst.load,
    '.md': md.load,
}

TEXTLOADERS = {
    '.rst': rst.load_string,
    '.md': md.load_string,
}


def metadata_file_name(dirname, fname):
    return posixpath.join(dirname, f'{fname}{miyadailu.METADATA_FILE_SUFFIX}')


def load_from_file(metadata:FileContent)->Tuple[Dict, str]:
    srcpath = metadata['srcpath']

    loaded:Dict = {}
    metadatafile = metadata_file_name(*os.path.split(srcpath))
    if os.path.exists(metadatafile):
        text = open(metadatafile, encoding=miyadaiku.YAML_ENCODING).read()
        loaded = yaml.load(text, Loader=yaml.FullLoader) or {}
        loaded['metadatafile'] = metadatafile
        
    ext = srcpath.suffix
    f = FILELOADERS.get(ext)
    if not f:
        return {}, ''
    d, html = f(srcpath)
    loaded.update(d)
    return loaded, html


def load_from_package(metadata:ThemeContent)->Tuple[Dict, str]:
    package = metadata['package']
    srcpath = metadata['srcpath']

    loaded:Dict = {}
    metadatafile = metadata_file_name(*os.path.split(srcpath))
    if pkg_resources.resource_exists(package, metadatafile):
        text = pkg_resources.resource_string(package, metadatafile)
        loaded = yaml.load(text, Loader=yaml.FullLoader) or {}
        loaded['metadatafile'] = metadatafile
        
    src = pkg_resources.resource_string(package, srcpath)

    ext = os.path.splitext(srcpath)[-1]
    f = TEXTLOADERS.get(ext)
    if not f:
        return {}, ''
    d, html = f(src)
    loaded.update(d)
    return loaded, html


