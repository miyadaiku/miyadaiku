from typing import (
    List,
    Iterator,
    Dict,
    Tuple,
    Optional,
    Set,
    Any,
    KeysView,
    ItemsView
)
import os
import fnmatch
import pkg_resources
from pathlib import Path, PurePath
import logging
import posixpath
import yaml

import miyadaiku
from miyadaiku import ContentPath, ContentSrc
from . import config, rst, md

logger = logging.getLogger(__name__)


def is_ignored(ignores: Set[str], name: str)->bool:
    if name.lower().endswith(miyadaiku.METADATA_FILE_SUFFIX):
        return True

    for p in ignores:
        if fnmatch.fnmatch(name, p):
            return True
    return False

def to_contentpath(path: str) -> ContentPath:
    spath = str(path)
    spath = spath.replace("\\", "/").strip("/")
    ret = path.split("/")

    for c in ret:
        if set(c.strip()) == set("."):
            raise ValueError("Invalid path: {path}")

    dir = tuple(ret[:-1])
    return (dir, ret[-1])



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
            metadatafile = os.path.join(dirname, f"{fname}{miyadaiku.METADATA_FILE_SUFFIX}")

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
        destname = srcpath [pathlen:]

        dirname, fname = posixpath.split(srcpath )
        metadatapath  = posixpath.join(dirname,f"{fname}{miyadaiku.METADATA_FILE_SUFFIX}")

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


def yamlloader(src: ContentSrc) -> Tuple[Dict[str, Any], Optional[str]]:
    text = src.read_bytes()
    metadata = yaml.load(text, Loader=yaml.FullLoader) or {}
    if "type" not in metadata:
        metadata["type"] = "config"

    return metadata, None


def binloader(src: ContentSrc) -> Tuple[Dict[str, Any], Optional[str]]:
    return {"type": "binary"}, None


FILELOADERS = {
    ".rst": rst.load,
    ".rest": rst.load,
    ".md": md.load,
    ".yml": yamlloader,
    ".yaml": yamlloader,
}


class ContentFiles:
    _contentfiles: Dict[ContentPath, Tuple[ContentSrc, Optional[str]]]

    def __init__(self)->None:
        self._contentfiles = {}

    def add(self, contentsrc: ContentSrc, body: Optional[str])->None:
        if contentsrc.contentpath not in self._contentfiles:
            self._contentfiles[contentsrc.contentpath] = (contentsrc, body)

    def get_contentfiles_keys(self)->KeysView[ContentPath]:
        return self._contentfiles.keys()

    def items(self)->ItemsView[ContentPath, Tuple[ContentSrc, Optional[str]]]:
        return self._contentfiles.items()

    # def has_content(self, key, base=None):
    #     dirname, filename = utils.abs_path(key, base.dirname if base else None)
    #     return (dirname, filename) in self._contentfiles

    # def get_content(self, key, base=None):
    #     dirname, filename = utils.abs_path(key, base.dirname if base else None)
    #     try:
    #         return self._contentfiles[(dirname, filename)]
    #     except KeyError:
    #         raise ContentNotFound(key) from None

    # def get_contentfiless(self, subdirs=None, base=None, filters=None, recurse=True):
    #     contents = [c for c in self._contentfiles.values()]

    #     if not filters:
    #         filters = {}

    #     filters = filters.copy()
    #     if "draft" not in filters:
    #         filters["draft"] = {False}
    #     if "type" not in filters:
    #         filters["type"] = {"article"}

    #     def f(content):
    #         for k, v in filters.items():
    #             if not hasattr(content, k):
    #                 return False
    #             prop = getattr(content, k)
    #             if isinstance(prop, str):
    #                 if prop not in v:
    #                     return False
    #             elif isinstance(prop, collections.abc.Collection):
    #                 for e in prop:
    #                     if e in v:
    #                         break
    #                 else:
    #                     return False
    #             else:
    #                 if prop not in v:
    #                     return False
    #         return True

    #     contents = [c for c in self._contentfiles.values() if f(c)]

    #     if subdirs:
    #         cur = base.dirname if base else None
    #         subdirs = [utils.abs_dir(d, cur) for d in subdirs]
    #         if recurse:
    #             cond = lambda c: any(c.dirname[: len(d)] == d for d in subdirs)
    #         else:
    #             cond = lambda c: c.dirname in subdirs

    #         contents = filter(cond, contents)

    #     recs = []
    #     for c in contents:
    #         d = c.date
    #         if d:
    #             ts = d.timestamp()
    #         else:
    #             ts = 0
    #         recs.append((ts, c))

    #     recs.sort(reverse=True, key=lambda r: (r[0], r[1].title))
    #     return [c for (ts, c) in recs]

    # def group_items(self, group, subdirs=None, base=None, filters=None, recurse=True):
    #     if not group:
    #         return [((), list(self.get_contentfiles(subdirs, base, filters, recurse)))]

    #     d = collections.defaultdict(list)
    #     for c in self.get_contentfiles(subdirs, base, filters, recurse):
    #         g = getattr(c, group, None)

    #         if g is not None:
    #             if isinstance(g, str):
    #                 d[(g,)].append(c)
    #             elif isinstance(g, collections.abc.Collection):
    #                 for e in g:
    #                     d[(e,)].append(c)
    #             else:
    #                 d[(g,)].append(c)

    #     return sorted(d.items())

    # @property
    # def categories(self):
    #     contents = self.get_contentfiles(filters={"type": {"article"}})
    #     categories = (getattr(c, "category", None) for c in contents)
    #     return sorted(set(c for c in categories if c))

    # @property
    # def tags(self):
    #     tags = set()
    #     for c in self.get_contentfiles(filters={"type": {"article"}}):
    #         t = getattr(c, "tags", None)
    #         if t:
    #             tags.update(t)
    #     return sorted(tags)


def loadfiles(
    files: ContentFiles,
    cfg: config.Config,
    root: Path,
    ignores: Set[str],
    themes: List[str],
) -> None:
    def loadfile(src: ContentSrc, bin:bool)->Optional[str]:
        if not bin:
            ext = os.path.splitext(src.srcpath)[1]
            loader = FILELOADERS.get(ext, binloader)
        else:
            loader = binloader

        metadata, body = loader(src)
        src.metadata.update(metadata)

        return body

    def load(walk:Iterator[ContentSrc], bin:bool=False) -> None:
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
