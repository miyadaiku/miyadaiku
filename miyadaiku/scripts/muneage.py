# type: ignore
import locale
import argparse
import sys
from pathlib import Path
import threading
import time
import multiprocessing
import http.server
import os

import miyadaiku.site
from . import observer
from .. import mp_log
from miyadaiku import OUTPUTS_DIR
import logging

logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_ALL, "")


def exec_server(dir, bind, port):
    os.chdir(dir)
    http.server.test(http.server.SimpleHTTPRequestHandler, bind=bind, port=port)


def build(path, props):
    site = miyadaiku.site.Site()
    site.load(path, props)
    ok, err, deps = site.build()
    

parser = argparse.ArgumentParser(description="Build miyadaiku project.")
parser.add_argument("directory", help="directory name")

parser.add_argument(
    "--version", "-v", action="version", version=f"{miyadaiku.__version__}"
)

parser.add_argument(
    "--define",
    "-d",
    action="append",
    metavar="property=value",
    help="Set default property value.",
)

parser.add_argument(
    "--traceback",
    "-t",
    action="store_true",
    default=False,
    help="Show traceback on error",
)

parser.add_argument(
    "--debug", "-D", action="store_true", default=False, help="Run debug mode"
)

parser.add_argument("--rebuild", "-r", action="store_true", help="Rebuild contents.")

parser.add_argument(
    "--watch", "-w", action="store_true", help="Watch for contents update."
)

parser.add_argument("--server", "-s", action="store_true", help="Run http server.")

parser.add_argument("--port", "-p", default=8800, type=int, help="http port")

parser.add_argument("--bind", "-b", default="0.0.0.0", help="Bind address")


def _main() -> None:
    args = parser.parse_args()

    props = {}
    for s in args.define or ():
        d = [p.strip() for p in s.split("=", 1)]
        if len(d) != 2:
            print(f"Invalid property: {s!r}", file=sys.stderr)
            sys.exit(1)
        props[d[0]] = d[1]

    d = Path(args.directory)

    if not d.exists() or not d.is_dir():
        print(f"'{d}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    mp_log.init_logging()

    outputs = d / OUTPUTS_DIR
    if not outputs.is_dir():
        outputs.mkdir()

    if args.server:
        server = multiprocessing.Process(
            target=exec_server,
            kwargs=dict(dir=str(outputs), port=args.port, bind=args.bind),
            daemon=True,
        )

        server.start()

    try:
        if not args.watch:
            print(f"Building {d.resolve()} ...")
            build(d, props)
        else:
            print(f"Watching {d.resolve()} ...")

            ev = threading.Event()

            obsrv = observer.create_observer(d, ev)
            obsrv.start()

            ev.set()  # run once at least
            while True:
                ev.wait()
                time.sleep(0.1)
                ev.clear()

                print(f"Building {d.resolve()} ...")
                build(d, props)

        if args.server:
            server.join()
    finally:
        if args.server:
            server.terminate()

    return


def main() -> None:
    multiprocessing.set_start_method("spawn")
    ret = _main()
    sys.exit(ret)


if __name__ == "__main__":
    main()
