import sys
import runpy
import locale
import argparse
import os
import pathlib
import time
import threading
import tzlocal
import happylogging
import logging
import http.server
import multiprocessing

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import miyadaiku.core
import miyadaiku.core.__version__
from miyadaiku.core.main import (Site, DEP_FILE, CONFIG_FILE,
                                 CONTENTS_DIR, FILES_DIR, TEMPLATES_DIR, OUTPUTS_DIR)
from miyadaiku.core.hooks import HOOKS, run_hook
OBSERVER = None


class ContentDirHandler(FileSystemEventHandler):
    def __init__(self, ev):
        self._ev = ev

    def on_created(self, event):
        if event.is_directory:
            return
        self._ev.set()

    def on_modified(self, event):
        if event.is_directory:
            return
        self._ev.set()

    def on_deleted(self, event):
        if event.is_directory:
            return
        self._ev.set()


DIRS = [CONTENTS_DIR, FILES_DIR, TEMPLATES_DIR]


class ConfigHandler(FileSystemEventHandler):
    def __init__(self, ev):
        self._ev = ev

    def on_created(self, event):
        if event.is_directory:
            if os.path.split(event.src_path)[1] in DIRS:
                OBSERVER.schedule(
                    ContentDirHandler(self._ev), event.src_path,
                    recursive=True)
            return

        if os.path.split(event.src_path)[1] == CONFIG_FILE:
            self._ev.set()

    def on_modified(self, event):
        if os.path.split(event.src_path)[1] == CONFIG_FILE:
            self._ev.set()

    def on_deleted(self, event):
        if os.path.split(event.src_path)[1] == CONFIG_FILE:
            self._ev.set()


def _create_observer(path, ev):
    observer = Observer()
    for subdir in DIRS:
        d = path / subdir
        if d.is_dir():
            observer.schedule(ContentDirHandler(ev), str(d), recursive=True)

    observer.schedule(ConfigHandler(ev), str(path), recursive=False)
    return observer


locale.setlocale(locale.LC_ALL, '')

parser = argparse.ArgumentParser(description='Build miyadaiku project.')
parser.add_argument('directory', help='directory name')

parser.add_argument('--version', '-v', action='version',
                    version=f'{miyadaiku.core.__version__.version}')

parser.add_argument('--define', '-d', action='append', metavar='property=value',
                    help='Set default property value.')

parser.add_argument('--traceback', '-t', action='store_true', default=False,
                    help="Show traceback on error")

parser.add_argument('--debug', '-D', action='store_true', default=False,
                    help="Run debug mode")

parser.add_argument('--rebuild', '-r', action='store_true',
                    help='Rebuild contents.')

parser.add_argument('--watch', '-w', action='store_true',
                    help='Watch for contents update.')

parser.add_argument('--server', '-s', action='store_true',
                    help='Run http server.')

parser.add_argument('--port', '-p', default=8800, type=int,
                    help='http port')

parser.add_argument('--bind', '-b', default='0.0.0.0',
                    help='Bind address')


def build(d, props, traceback=False, debug=False):
    run_hook(HOOKS.start, d, props)

    site = Site(d, props, traceback, debug)
    site.pre_build()
    code = site.build()

    run_hook(HOOKS.finished, site, code, site)


def load_hook(d):
    modules = (d / 'modules').resolve()
    if modules.is_dir():
        sys.path.insert(0, modules)

    hook = (d / 'hooks.py').resolve()
    if hook.exists():
        runpy.run_path(str(hook))


def run_server(dir, *args, **kwargs):
    os.chdir(dir)
    http.server.test(*args, **kwargs)


def _main():
    global OBSERVER

    args = parser.parse_args()
    miyadaiku.core.DEBUG = args.debug

    lv = 'DEBUG' if miyadaiku.core.DEBUG else 'INFO'
    happylogging.initlog(filename='-', level=lv)
    logging.error.setcolor("RED")

    props = {}
    for s in args.define or ():
        d = [p.strip() for p in s.split('=', 1)]
        if len(d) != 2:
            print(f'Invalid property: {s!r}', file=sys.stderr)
            sys.exit(1)
        props[d[0]] = d[1]

    d = pathlib.Path(args.directory)

    load_hook(d)

    if args.rebuild:
        deppath = d / DEP_FILE
        try:
            deppath.unlink()
        except IOError:
            pass

    if args.server:
        outputs = d / OUTPUTS_DIR
        if not outputs.is_dir():
            outputs.mkdir()

        t = multiprocessing.Process(
            target=run_server,
            args=(str(outputs), http.server.SimpleHTTPRequestHandler,),
            kwargs=dict(port=args.port, bind=args.bind),
            daemon=True)

        t.start()

    try:
        code = build(d, props, args.traceback, miyadaiku.core.DEBUG)
        if args.watch:
            print(f'Watching {d.resolve()} ...')

            ev = threading.Event()

            OBSERVER = _create_observer(d, ev)
            OBSERVER.start()

            while True:
                ev.wait()
                time.sleep(0.1)
                ev.clear()

                build(d, props, args.traceback, miyadaiku.core.DEBUG)

        if args.server:
            t.join()
    finally:
        if args.server:
            t.terminate()

    return code


def main():
    code = _main()
    sys.exit(code)


if __name__ == '__main__':
    main()
