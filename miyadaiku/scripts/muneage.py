# type: ignore
import argparse
import datetime
import http.server
import locale
import logging
import multiprocessing
import os
import signal
import sys
import threading
import time
from pathlib import Path

import miyadaiku.site
from miyadaiku import OUTPUTS_DIR

from .. import mp_log
from . import observer

logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_ALL, "")


class MiyadaikuHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("cache-control", "no-cache")
        return super().end_headers()


def exec_server(dir, bind, port):
    os.chdir(dir)
    http.server.test(MiyadaikuHTTPHandler, bind=bind, port=port)


def build(path, outputdir, props, args):
    print(f"Building {path.resolve()} ...")
    start = datetime.datetime.now()

    site = miyadaiku.site.Site(rebuild=args.rebuild, debug=args.debug)
    site.load(path, props, outputdir)
    ok, err, *_ = site.build()

    finished = datetime.datetime.now()
    secs = (finished - start).total_seconds()
    msg = f"""Build finished at {finished}(ellapsed: {secs} secs)
Built {ok} files. {err} error found.
"""

    if err:
        mp_log.Color.RED.value + msg + mp_log.Color.RESET.value
    print(msg)

    return err


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


parser.add_argument("--output", "-o", default="", type=str, help="Output direcotry")

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

    if args.output:
        outputs = Path(args.output)
    else:
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
            err = build(d, outputs, props, args)
            if args.server:
                server.join()
            return 1 if err else 0
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

                build(d, outputs, props, args)

        if args.server:
            server.join()
    finally:
        if args.server:
            server.terminate()

    return


def main() -> None:
    multiprocessing.set_start_method("spawn")

    try:
        ret = _main()
    except KeyboardInterrupt:
        sys.exit(0x80 + signal.SIGINT)

    sys.exit(ret)


if __name__ == "__main__":
    main()
