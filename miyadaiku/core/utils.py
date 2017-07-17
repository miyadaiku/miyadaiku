import os
import pathlib
import unicodedata
import pkg_resources
import posixpath
import re


def walk(path):
    articles = []
    path = path.expanduser().resolve()
    for root, dirs, files in os.walk(path):
        root = pathlib.Path(root)
        for file in files:
            articles.append(root / file)

    return articles


def walk_package(package, dir):
    if dir.endswith('/'):
        dir = dir[:-1]

    if not pkg_resources.resource_isdir(package, dir):
        return

    children = pkg_resources.resource_listdir(package, dir)
    for child in children:
        p = f'{dir}/{child}'
        if pkg_resources.resource_isdir(package, p):
            yield from walk_package(package, p)
        else:
            yield p


def abs_path(relpath, dirtuple=None):
    if not isinstance(relpath, str):
        return relpath
    d, f = posixpath.split(relpath)
    d = abs_dir(d, dirtuple)
    return d, f


def abs_dir(d, dirtuple=None):
    if not isinstance(d, str):
        return d

    if not d.startswith('/'):
        if dirtuple is None:
            raise ValueError(f'relpath without base directory: {d}')

        dir = '/'.join(dirtuple) or '/'
        d = posixpath.join(dir, d)

    d = posixpath.normpath(d)
    if d == '.':
        d = ()
    else:
        d = dirname_to_tuple(d)
    return d


def format_dirname(dirname):
    return dirname.replace('\\', '/').strip('/')


def dirname_to_tuple(dirname):
    if isinstance(dirname, tuple):
        return dirname

    assert not dirname.startswith('.')

    dirname = format_dirname(dirname)
    if dirname:
        dirname = tuple(dirname.split('/'))
    else:
        dirname = ()
    return dirname


def slugify(value):
    value = unicodedata.normalize('NFKC', value)
    value = re.sub('[^\w\s-]', '', value).strip().lower()
    value = '-'.join(value.split())
    return value
