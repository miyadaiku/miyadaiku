import sys
import locale
import argparse
import os
import pathlib
import tzlocal
import happylogging
import logging

import miyadaiku.core
from miyadaiku.core.main import Site

locale.setlocale(locale.LC_ALL, '')

parser = argparse.ArgumentParser(description='Build miyadaiku project.')
parser.add_argument('directory', help='directory name')
parser.add_argument('--define', '-d', action='append', metavar='property=value',
                    help='Set default property value.')

parser.add_argument('--debug', '-D', action='store_true', default=False,
                    help="Show debug message")


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
    site = Site(d, props)

    site.pre_build()
    return site.build()


def main():
    code = _main()
    sys.exit(code)


if __name__ == '__main__':
    main()
