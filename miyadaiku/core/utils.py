import os
import pathlib
import unicodedata
import pkg_resources
import posixpath
import re
import random
import time
import traceback


def walk(path):
    articles = []
    path = path.expanduser().resolve()
    for root, dirs, files in os.walk(path):
        root = pathlib.Path(root)
        if root.stem.startswith('.'):
            continue
        for file in files:
            if file.startswith('.'):
                continue
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

    assert not dirname.startswith('./')
    assert not dirname.startswith('../')

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


MKDIR_MAX_RETRY = 5
MKDIR_WAIT = 0.1


def prepare_output_path(path, dirname, name):
    dir = path.joinpath(*dirname)
    name = name.strip('/\\')
    dest = os.path.expanduser((dir / name))
    dest = os.path.normpath(dest)

    s = str(path)
    if not dest.startswith(s) or dest[len(s)] not in '\\/':
        raise ValueError(f"Invalid file name: {dest}")

    dirname = os.path.split(dest)[0]
    for i in range(MKDIR_MAX_RETRY):
        if os.path.isdir(dirname):
            break
        try:
            os.makedirs(dirname, exist_ok=True)
        except IOError:
            pass

        time.sleep(MKDIR_WAIT * random.random())

    if os.path.exists(dest):
        os.unlink(dest)

    return dest


def nthlines(src, lineno):
    #    if src is None:
    #        try:
    #            if filename and os.path.exists(filename):
    #                src = open(filename).read()
    #        except IOError:
    #            src = ''
    #
    #    if not src:
    #        return ''
    #
    if not src:
        return ''
    src = src.split('\n')
    f = max(0, lineno - 3)
    lines = []
    for n in range(f, min(f + 5, len(src))):
        if n == (lineno - 1):
            lines.append('  >>> ' + src[n])
        else:
            lines.append('      ' + src[n])

    lines = "\n".join(lines).rstrip() + '\n'
    return lines


def get_last_frame_file(e):
    frame, lineno = next(traceback.walk_tb(e.__traceback__))
    return frame.f_code.co_filename, lineno
