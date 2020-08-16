from __future__ import annotations

import collections.abc
import fnmatch
import logging
import os
import posixpath
import time
from pathlib import Path
from typing import (
    Any,
    Dict,
    ItemsView,
    Iterable,
    Iterator,
    KeysView,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)

import importlib_resources
import yaml

import miyadaiku
from miyadaiku import ContentPath, ContentSrc, PathTuple, to_contentpath

from . import config, contents, exceptions, extend, html, site
from .contents import Content

logger = logging.getLogger(__name__)


def is_ignored(ignores: Set[str], name: str) -> bool:
    if name.lower().endswith(miyadaiku.METADATA_FILE_SUFFIX):
        return True

    basename = os.path.basename(name)
    for p in ignores:
        if fnmatch.fnmatch(basename, p):
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

            metadata: Dict[Any, Any] = {}

            if os.path.isfile(metadatafile):
                text = open(metadatafile, encoding=miyadaiku.YAML_ENCODING).read()
                metadata = yaml.load(text, Loader=yaml.FullLoader) or {}

            mtime = filename.stat().st_mtime
            yield ContentSrc(
                package="",
                srcpath=str(filename),
                metadata=metadata,
                contentpath=to_contentpath(str(filename.relative_to(path))),
                mtime=mtime,
            )


def _iter_package_files(path: Path, ignores: Set[str]) -> Iterator[Path]:
    children = path.iterdir()
    for child in children:
        if is_ignored(ignores, str(child)):
            continue

        if child.is_dir():
            yield from _iter_package_files(child, ignores)
        else:
            yield child


def walk_package(package: str, path: str, ignores: Set[str]) -> Iterator[ContentSrc]:
    logger.info(f"Loading {package}/{path}")

    if not path.endswith("/"):
        path = path + "/"

    packagepath = importlib_resources.files(package)
    root = packagepath / path
    if not root.is_dir():
        return

    for srcpath in _iter_package_files(root, ignores):
        destname = posixpath.relpath(srcpath, root)

        dirname, fname = posixpath.split(posixpath.relpath(srcpath, packagepath))

        metadatapath = (
            srcpath.parent / f"{srcpath.name}{miyadaiku.METADATA_FILE_SUFFIX}"
        )

        if metadatapath.exists():
            text = metadatapath.read_bytes()
            metadata = yaml.load(text, Loader=yaml.FullLoader) or {}
        else:
            metadata = {}

        yield ContentSrc(
            package=package,
            srcpath=str(posixpath.relpath(srcpath, packagepath)),
            metadata=metadata,
            contentpath=to_contentpath(destname),
            mtime=None,
        )


def yamlloader(src: ContentSrc) -> Sequence[Tuple[ContentSrc, None]]:
    text = src.read_bytes()
    metadata = yaml.load(text, Loader=yaml.FullLoader) or {}
    if not isinstance(metadata, (dict, list, tuple)):
        logger.error(f"Error: {src.repr_filename()} is not valid YAML file.")

    if "type" not in metadata:
        metadata["type"] = "config"

    src.metadata.update(metadata)
    return [(src, None)]


def binloader(src: ContentSrc) -> Sequence[Tuple[ContentSrc, Optional[str]]]:
    src.metadata["type"] = "binary"
    return [(src, None)]


def rstloader(src: ContentSrc) -> Sequence[Tuple[ContentSrc, Optional[str]]]:
    from . import rst

    return rst.load(src)


def mdloader(src: ContentSrc) -> Sequence[Tuple[ContentSrc, Optional[str]]]:
    from . import md

    return md.load(src)


def ipynbloader(src: ContentSrc) -> Sequence[Tuple[ContentSrc, Optional[str]]]:
    from . import ipynb

    return ipynb.load(src)


def txtloader(src: ContentSrc) -> Sequence[Tuple[ContentSrc, Optional[str]]]:
    from . import text

    return text.load(src)


FILELOADERS = {
    ".rst": rstloader,
    ".rest": rstloader,
    ".md": mdloader,
    ".html": html.load,
    ".htm": html.load,
    ".j2": html.load,
    ".yml": yamlloader,
    ".yaml": yamlloader,
    ".ipynb": ipynbloader,
    ".txt": txtloader,
}


class ContentFiles:
    _contentfiles: Dict[ContentPath, Content]
    mtime: float

    def __init__(self) -> None:
        self._contentfiles = {}
        self.mtime = time.time()

    def add(self, contentsrc: ContentSrc, body: Optional[bytes]) -> None:
        if contentsrc.contentpath not in self._contentfiles:
            content = contents.build_content(contentsrc, body)
            self._contentfiles[contentsrc.contentpath] = content
        # todo: emit log message

    def add_bytes(self, type: str, path: str, body: bytes) -> Content:
        cpath = to_contentpath(path)

        contentsrc = ContentSrc(
            package=None,
            srcpath=None,
            metadata={"type": type},
            contentpath=cpath,
            mtime=0,
        )

        content = contents.build_content(contentsrc, body)
        self._contentfiles[content.src.contentpath] = content
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
            raise exceptions.ContentNotFound(path) from None

    def get_contents(
        self,
        site: site.Site,
        filters: Optional[Dict[str, Any]] = None,
        excludes: Optional[Dict[str, Any]] = None,
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

        def adj(content: Content, filters: Dict[str, Any]) -> bool:
            notfound = object()
            for k, v in filters.items():
                prop = content.get_metadata(site, k, notfound)
                if prop is notfound:
                    if v is None:
                        continue
                    else:
                        return False

                if isinstance(prop, str):
                    if v is None:
                        return False

                    if prop not in v:
                        return False

                elif isinstance(prop, collections.abc.Collection):
                    if v is None:
                        if not prop:
                            continue
                        else:
                            return False

                    for e in prop:
                        if e in v:
                            break
                    else:
                        return False
                else:
                    if v is None:
                        return False

                    if prop not in v:
                        return False
            return True

        contents = [c for c in self._contentfiles.values() if adj(c, filters_copy)]

        if excludes:
            contents = [c for c in contents if not adj(c, excludes)]

        if subdirs is not None:
            dirs = subdirs
            if recurse:
                cond = lambda c: any(c.get_parent()[: len(d)] == d for d in dirs)
            else:
                cond = lambda c: c.get_parent() in dirs

            contents = filter(cond, contents)

        recs = []
        for c in contents:
            d = c.get_metadata(site, "updated", None)
            if d:
                updated = d.timestamp()
            else:
                updated = 0

            title = c.get_metadata(site, "title")
            recs.append((updated, title, c))

        recs.sort(reverse=True, key=lambda r: (r[0], r[1]))
        return [rec[2] for rec in recs]

    def group_items(
        self,
        site: site.Site,
        group: str,
        filters: Optional[Dict[str, Any]] = None,
        excludes: Optional[Dict[str, Any]] = None,
        subdirs: Optional[Sequence[PathTuple]] = None,
        recurse: bool = True,
    ) -> List[Tuple[Tuple[str, ...], List[Content]]]:

        if not group:
            return [
                ((), list(self.get_contents(site, filters, excludes, subdirs, recurse)))
            ]

        d = collections.defaultdict(list)
        for c in self.get_contents(site, filters, excludes, subdirs, recurse):
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


def loadfile(src: ContentSrc, bin: bool) -> List[Tuple[ContentSrc, Optional[bytes]]]:
    if not bin:
        assert src.srcpath
        ext = os.path.splitext(src.srcpath)[1]
        loader = FILELOADERS.get(ext, binloader)
    else:
        loader = binloader

    ret: List[Tuple[ContentSrc, Optional[bytes]]] = []
    for contentsrc, body in loader(src):
        if isinstance(body, bytes):
            ret.append((contentsrc, body))
        if isinstance(body, str):
            ret.append((contentsrc, body.encode("utf-8")))
        else:
            ret.append((contentsrc, None))
    return ret


def loadfiles(
    site: site.Site,
    files: ContentFiles,
    cfg: config.Config,
    root: Path,
    ignores: Set[str],
    themes: List[str],
) -> None:
    def load(walk: Iterator[ContentSrc], bin: bool = False) -> None:
        f: Optional[ContentSrc]
        for f in walk:
            if not f:
                continue

            f = extend.run_pre_load(site, f, bin)
            if not f:
                continue

            for f, body in loadfile(f, bin):
                if not f:
                    continue

                f, body = extend.run_post_load(site, f, bin, body)

                if not f:
                    continue

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

    extend.run_load_finished(site)
