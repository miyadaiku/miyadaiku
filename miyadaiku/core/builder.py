import sys
import pickle
import pathlib
import importlib
import hashlib
import os
import io
import logging
import enum
import shutil
import yaml
import traceback
import collections
import dateutil.parser
import concurrent.futures
import jinja2.exceptions


import miyadaiku.core
from . import config
from . import site
from . import contents
from . import jinjaenv
from . exception import MiyadaikuBuildError
from .hooks import run_hook, HOOKS

logger = logging.getLogger(__name__)

DEP_FILE = '_depends.pickle'
DEP_VER = '1.1.0'


class Depends:
    rebuild = False
    def __init__(self, site):
        self.site = site
        self._load()

    def _load(self):
        self.rebuild = False
        self.depends = collections.defaultdict(set)
        self.rebuild_always = set()
        self.metadatas = None

        deppath = self.site.path / DEP_FILE
        try:
            with open(deppath, "rb") as f:
                ver, keys, values = pickle.load(f)

            if ver != DEP_VER:
                self.rebuild = True
                return
            rebuild_always, deps, metadatas = values
        except Exception:
            self.rebuild = True
            return

        self.keys = keys
        self.depends = deps
        self.rebuild_always = rebuild_always
        self.metadatas = metadatas
        self.stat_depfile = os.stat(deppath)

    def get_metadatas(self):
        all = {}
        for k, c in self.site.contents.items():
            m = dict(c.metadata)
            all[k] = m

        return all

    def check_rebuild(self):
        if self.rebuild:
            return

        if not self.stat_depfile:
            self.rebuild = True
            return

        if self.metadatas != self.get_metadatas():
            self.rebuild = True
            return

        if self.site.stat_config:
            if self.site.stat_config.st_mtime > self.stat_depfile.st_mtime:
                self.rebuild = True
                return

        for root, dirs, files in os.walk(self.site.path / site.MODULES_DIR):
            root = pathlib.Path(root)
            for file in files:
                if (root / file).stat().st_mtime > self.stat_depfile.st_mtime:
                    self.rebuild = True
                    return

        for root, dirs, files in os.walk(self.site.path / site.TEMPLATES_DIR):
            root = pathlib.Path(root)
            for file in files:
                if (root / file).stat().st_mtime > self.stat_depfile.st_mtime:
                    self.rebuild = True
                    return

        curkeys = set(self.site.contents.get_contents_keys())
        created = curkeys - self.keys
        deleted = self.keys - curkeys

        if deleted or created:
            self.rebuild = True
            return

        for key, content in self.site.contents.items():
            if isinstance(content, contents.ConfigContent):
                if content.is_updated(self.stat_depfile.st_mtime):
                    self.rebuild = True
                    return

    def check_content_update(self):
        updated_items = []

        for key, content in self.site.contents.items():
            if (key in self.rebuild_always) or content.is_updated(self.stat_depfile.st_mtime):
                updated_items.append(content)
                content.updated = True

        seen = set()
        while updated_items:
            updated = []
            for content in updated_items:
                refs = self.depends.get((content.dirname, content.name), ())
                for ref, pagearg in refs:
                    if self.site.contents.has_content(ref):
                        c = self.site.contents.get_content(ref)
                        if c not in seen:
                            if not c.updated:
                                c.updated = True
                                updated.append(c)
                            seen.add(c)

            updated_items = updated

    def save(self):
        keys = set(self.site.contents.get_contents_keys())
        metadatas = self.get_metadatas()
        o = (DEP_VER, keys, (self.rebuild_always, self.depends, metadatas))

        try:
            with open(self.site.path / DEP_FILE, "wb") as f:
                pickle.dump(o, f)
        except IOError as e:
            logger.warn(f'Falied to write {self.site.path / DEP_FILE}: {e}')

def _exc_to_dict(content, e):
    t = io.StringIO()
    traceback.print_exception(type(e), e, e.__traceback__, file=t)
    tb = t.getvalue()

    if not isinstance(e, MiyadaikuBuildError):
        e = MiyadaikuBuildError(e, content, None, None)
    ret = e.to_dict()
    ret['tb'] = tb
    return ret

def _run_build(key):
    content = _site.contents.get_content(key)
    logger.info(f'Building {content.srcfilename}')

    output_path = _site.path / site.OUTPUTS_DIR
    run_hook(HOOKS.pre_build, _site, content, output_path)
    try:
        destfiles, context = content.build(output_path)
    except Exception as e:
        if _site.debug or _site.show_traceback:
            traceback.print_exc()
        d = _exc_to_dict(content, e)
        return None, True, d

    run_hook(HOOKS.post_build, _site, content, output_path, destfiles)

    src = (content.dirname, content.name)

    deps = collections.defaultdict(set)
    refs, pageargs = context.get_depends()
    for ref in refs:
        if 'package' in ref.metadata:
            continue
        deps[(ref.dirname, ref.name)].add((src, pageargs))

    return deps, context.is_rebuild_always(), None


def _build_result(site, deps, content, dep, rebuild_always, d, errors):
    if rebuild_always:
        deps.rebuild_always.add((content.dirname, content.name))

    if dep is None:
        _print_err_dict(site, d)
        errors.append(d)
        return

    for k, v in dep.items():
        deps.depends[k].update(v)

def _print_err_dict(site, d):
    logger.error(f'Error in {d["srcfilename"]} while building {d["pagefilename"]}')
    logger.error(f'  {d["exctype"]}: {str(d["args"][0]).rstrip()}')

    if site.show_traceback:
        logger.error(d['tb'])


def build(site):

    deps = Depends(site)
    deps.check_rebuild()
    if not deps.rebuild:
        deps.check_content_update()

    global _site
    _site = site

    if sys.platform in ('win32', 'darwin'):
        executor = concurrent.futures.ThreadPoolExecutor()
    else:
        executor = concurrent.futures.ProcessPoolExecutor()

    errors = []

    def done(f, key):
        content = site.contents.get_content(key)
        dep, rebuild_always, d = f.result()
        _build_result(site, deps, content, dep, rebuild_always, d, errors)

    for key, content in site.contents.items():
        if not deps.rebuild and not content.updated:
            continue

        if site.debug:
            dep, rebuild_always, d = _run_build(key)
            _build_result(site, deps, content, dep, rebuild_always, d, errors)
        else:
            f = executor.submit(_run_build, key)
            f.add_done_callback(lambda f, key=key: done(f, key))

    executor.shutdown()

    deps.save()

    if not errors:
        logger.info(f'no errors')
    else:
        logger.error(f'total: {len(errors)} errors')
