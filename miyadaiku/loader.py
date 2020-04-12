from __future__ import annotations

from typing import (
    List,
    Iterator,
    Dict,
    Tuple,
    Optional,
    Set,
    Any,
    KeysView,
    ItemsView,
    Sequence,
    Iterable,
)
import os
import fnmatch
import pkg_resources
from pathlib import Path
import logging
import posixpath
import collections.abc
import yaml

import miyadaiku
from miyadaiku import ContentPath, ContentSrc, PathTuple, to_contentpath
from . import config, rst, md, contents, html
from . import site
from .contents import Content

logger = logging.getLogger(__name__)


def is_ignored(ignores: Set[str], name: str) -> bool:
    if name.lower().endswith(miyadaiku.METADATA_FILE_SUFFIX):
        return True

    for p in ignores:
        if fnmatch.fnmatch(name, p):
            return True
    return False



def walk_directory(path: Path, ignores: Set[str]) -> Iterator[ContentSrc]:
    logger.info(f"Loading {path}")
    path = path.expanduser().resolve()
    if not path.is_dir():
        return

    for root, dirs, files in os.walk(path):
        rootpath = Path(root)
        if rootpath.stem.startswith("."):
            continue

        dirs[:] = (dirname for dirname in dirs if not is_ignored(ignores, dirname))
        filenames = (
            filename for filename in files if not is_ignored(ignores, filename)
        )

        for name in filenames:
            filename = (rootpath / name).resolve()

            dirname, fname = os.path.split(filename)
            metadatafile = os.path.join(
                dirname, f"{fname}{miyadaiku.METADATA_FILE_SUFFIX}"
            )

            if os.path.isfile(metadatafile):
                text = open(metadatafile, encoding=miyadaiku.YAML_ENCODING).read()
                metadata = yaml.load(text, Loader=yaml.FullLoader) or {}
            else:
                metadata = {}
            mtime = filename.stat().st_mtime
            yield ContentSrc(
                package="",
                srcpath=str(filename),
                metadata=metadata,
                contentpath=to_contentpath(str(filename.relative_to(path))),
                mtime=mtime,
            )


def _iter_package_files(package: str, path: str, ignores: Set[str]) -> Iterator[str]:
    children = pkg_resources.resource_listdir(package, path)
    for child in children:
        if is_ignored(ignores, child):
            continue

        p = f"{path}{child}"
        if pkg_resources.resource_isdir(package, p):
            yield from _iter_package_files(package, p + "/", ignores)
        else:
            yield p


def walk_package(package: str, path: str, ignores: Set[str]) -> Iterator[ContentSrc]:
    logger.info(f"Loading {package}/{path}")

    if not path.endswith("/"):
        path = path + "/"
    pathlen = len(path)

    if not pkg_resources.resource_isdir(package, path):
        return

    for srcpath in _iter_package_files(package, path, ignores):
        destname = srcpath[pathlen:]

        dirname, fname = posixpath.split(srcpath)
        metadatapath = posixpath.join(
            dirname, f"{fname}{miyadaiku.METADATA_FILE_SUFFIX}"
        )

        if pkg_resources.resource_exists(package, metadatapath):
            text = pkg_resources.resource_string(package, metadatapath)
            metadata = yaml.load(text, Loader=yaml.FullLoader) or {}
        else:
            metadata = {}

        yield ContentSrc(
            package=package,
            srcpath=str(srcpath),
            metadata=metadata,
            contentpath=to_contentpath(destname),
            mtime=0,
        )


def yamlloader(src: ContentSrc) -> Tuple[Dict[str, Any], Optional[bytes]]:
    text = src.read_bytes()
    metadata = yaml.load(text, Loader=yaml.FullLoader) or {}
    if "type" not in metadata:
        metadata["type"] = "config"

    return metadata, None


def binloader(src: ContentSrc) -> Tuple[Dict[str, Any], Optional[bytes]]:
    return {"type": "binary"}, None


FILELOADERS = {
    ".rst": rst.load,
    ".rest": rst.load,
    ".md": md.load,
    ".html": html.load,
    ".htm": html.load,
    ".yml": yamlloader,
    ".yaml": yamlloader,
}


class ContentNotFound(Exception):
    content: Optional[Content] = None

    def set_content(self, content: Content) -> None:
        if not self.content:
            self.content = content
            self.args = (
                f"{self.content.src.contentpath}: `{self.args[0]}` is not found",
            )


class ContentFiles:
    _contentfiles: Dict[ContentPath, Content]

    def __init__(self) -> None:
        self._contentfiles = {}

    def add(self, contentsrc: ContentSrc, body: Optional[bytes]) -> None:
        if contentsrc.contentpath not in self._contentfiles:
            content = contents.build_content(contentsrc, body)
            self._contentfiles[contentsrc.contentpath] = content
        # todo: emit log message


    def add_bytes(self, type:str, path: str, body:bytes)->Content:
        cpath = to_contentpath(path)

        contentsrc = ContentSrc(
            package="",
            srcpath=path,
            metadata={'type':type},
            contentpath=cpath,
            mtime=0,
        )

        content = contents.build_content(contentsrc, body)
        self._contentfiles[contentsrc.contentpath] = content
        return content

    def get_contentfiles_keys(self) -> KeysView[ContentPath]:
        return self._contentfiles.keys()

    def items(self) -> ItemsView[ContentPath, Content]:
        return self._contentfiles.items()

    def has_content(self, path: ContentPath) -> bool:
        return path in self._contentfiles

    def get_content(self, path: ContentPath) -> Content:
        try:
            return self._contentfiles[path]
        except KeyError:
            raise ContentNotFound(path) from None

    def get_contents(
        self,
        site: site.Site,
        filters: Optional[Dict[str, Any]] = None,
        subdirs: Optional[Sequence[PathTuple]] = None,
        recurse: bool = True,
    ) -> List[Content]:
        contents: Iterable[Content] = [c for c in self._contentfiles.values()]

        if filters is None:
            filters_copy = {}
        else:
            filters_copy = filters.copy()

        if "draft" not in filters_copy:
            filters_copy["draft"] = {False}
        if "type" not in filters_copy:
            filters_copy["type"] = {"article"}

        def f(content: Content) -> bool:
            notfound = object()
            for k, v in filters_copy.items():
                prop = content.get_metadata(site, k, notfound)
                if prop is notfound:
                    return False

                if isinstance(prop, str):
                    if prop not in v:
                        return False
                elif isinstance(prop, collections.abc.Collection):
                    for e in prop:
                        if e in v:
                            break
                    else:
                        return False
                else:
                    if prop not in v:
                        return False
            return True

        contents = [c for c in self._contentfiles.values() if f(c)]

        if subdirs is not None:
            dirs = subdirs
            if recurse:
                cond = lambda c: any(c.get_parent()[: len(d)] == d for d in dirs)
            else:
                cond = lambda c: c.get_parent() in dirs

            contents = filter(cond, contents)

        recs = []
        for c in contents:
            d = c.get_metadata(site, "date", None)
            if d:
                ts = d.timestamp()
            else:
                ts = 0
            recs.append((ts, c))

        recs.sort(reverse=True, key=lambda r: (r[0], r[1].get_metadata(site, "title")))
        return [c for (ts, c) in recs]

    def group_items(
        self,
        site: site.Site,
        group: str,
        filters: Optional[Dict[str, Any]] = None,
        subdirs: Optional[Sequence[PathTuple]] = None,
        recurse: bool = True,
    ) -> List[Tuple[Tuple[str, ...], List[Content]]]:

        if not group:
            return [((), list(self.get_contents(site, filters, subdirs, recurse)))]

        d = collections.defaultdict(list)
        for c in self.get_contents(site, filters, subdirs, recurse):
            g = c.get_metadata(site, group, None)

            if g is not None:
                if isinstance(g, str):
                    d[(g,)].append(c)
                elif isinstance(g, collections.abc.Collection):
                    for e in g:
                        d[(e,)].append(c)
                else:
                    d[(g,)].append(c)

        return sorted(d.items())


def loadfile(src: ContentSrc, bin: bool) -> Optional[bytes]:
    if not bin:
        ext = os.path.splitext(src.srcpath)[1]
        loader = FILELOADERS.get(ext, binloader)
    else:
        loader = binloader

    metadata, body = loader(src)
    src.metadata.update(metadata)

    if isinstance(body, bytes):
        return body
    if isinstance(body, str):
        return body.encode("utf-8")
    else:
        return None


def loadfiles(
    files: ContentFiles,
    cfg: config.Config,
    root: Path,
    ignores: Set[str],
    themes: List[str],
) -> None:
    def load(walk: Iterator[ContentSrc], bin: bool = False) -> None:
        for f in walk:
            body = loadfile(f, bin)

            if bin:
                files.add(f, body)
            elif f.metadata["type"] == "config":
                cfg.add(f.contentpath[0], f.metadata, f)
            else:
                files.add(f, body)

    load(walk_directory(root / miyadaiku.CONTENTS_DIR, ignores))
    load(walk_directory(root / miyadaiku.FILES_DIR, ignores), bin=True)

    for theme in themes:
        load(walk_package(theme, miyadaiku.CONTENTS_DIR, ignores))
        load(walk_package(theme, miyadaiku.FILES_DIR, ignores), bin=True)
