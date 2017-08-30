import sys
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
from miyadaiku.core.main import (Site, DEP_FILE, CONFIG_FILE,
                                 CONTENTS_DIR, FILES_DIR, TEMPLATES_DIR, OUTPUTS_DIR)


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


class ConfigHandker(FileSystemEventHandler):
    def __init__(self, ev):
        self._ev = ev

    def on_created(self, event):
        if os.path.split(event.src_path)[1] == CONFIG_FILE:
            self._ev.set()

    def on_modified(self, event):
        if os.path.split(event.src_path)[1] == CONFIG_FILE:
            self._ev.set()

    def on_deleted(self, event):
        if os.path.split(event.src_path)[1] == CONFIG_FILE:
            self._ev.set()


locale.setlocale(locale.LC_ALL, '')

parser = argparse.ArgumentParser(description='Build miyadaiku project.')
parser.add_argument('directory', help='directory name')
parser.add_argument('--define', '-d', action='append', metavar='property=value',
                    help='Set default property value.')

parser.add_argument('--debug', '-D', action='store_true', default=False,
                    help="Show debug message")

parser.add_argument('--rebuild', '-r', action='store_true',
                    help='Rebuild contents.')

parser.add_argument('--watch', '-w', action='store_true',
                    help='Watch for contents update.')

parser.add_argument('--server', '-s', action='store_true',
                    help='Run http server.')

parser.add_argument('--port', '-p', default=8800, type=int,
                    help='http port')

parser.add_argument('--bind', '-b', default='0.0.0.0',
                    help='bind address')


def run_build(d, props):
    site = Site(d, props)
    site.pre_build()
    return site.build()


def run_server(dir, *args, **kwargs):
    os.chdir(dir)
    http.server.test(*args, **kwargs)


def _main():
    args = parser.parse_args()
    miyadaiku.core.DEBUG = args.debug

    lv = 'DEBUG' if miyadaiku.core.DEBUG else 'INFO'

    happylogging.initlog(filename='-', level=lv)

    logging.warning.setcolor("GREEN")
    logging.error.setcolor("RED")
    logging.exception.setcolor("RED")

    props = {}
    for s in args.define or ():
        d = [p.strip() for p in s.split('=', 1)]
        if len(d) != 2:
            print(f'Invalid property: {s!r}', file=sys.stderr)
            sys.exit(1)
        props[d[0]] = d[1]

    d = pathlib.Path(args.directory)

    if args.rebuild:
        deppath = d / DEP_FILE
        try:
            deppath.unlink()
        except IOError:
            pass

    if args.server:
        t = multiprocessing.Process(
            target=run_server,
            args=(str(d / OUTPUTS_DIR), http.server.SimpleHTTPRequestHandler,),
            kwargs=dict(port=args.port, bind=args.bind),
            daemon=True)

        t.start()

    try:
        site = Site(d, props)
        site.pre_build()
        code = site.build()

        if args.watch:
            print(f'Watching {d.resolve()} ...')

            ev = threading.Event()

            observer = Observer()
            observer.schedule(ContentDirHandler(ev), str(d / CONTENTS_DIR), recursive=True)
            observer.schedule(ContentDirHandler(ev), str(d / FILES_DIR), recursive=True)
            observer.schedule(ContentDirHandler(ev), str(d / TEMPLATES_DIR), recursive=True)
            observer.schedule(ConfigHandker(ev), str(d), recursive=False)
            observer.start()

            while True:
                ev.wait()
                time.sleep(0.1)
                ev.clear()

                b = multiprocessing.Process(
                    target=run_build,
                    args=(d, props))
                b.start()
                b.join()

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
