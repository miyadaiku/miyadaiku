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
                    help="Don't use fork waker")


def _main():
    happylogging.initlog(filename='-', level='DEBUG')
    logging.warning.setcolor("RED")
    logging.error.setcolor("RED")
    logging.exception.setcolor("RED")
    args = parser.parse_args()

    props = {}
    for s in args.define or ():
        d = [p.strip() for p in s.split('=', 1)]
        if len(d) != 2:
            print(f'Invalid property: {s!r}', file=sys.stderr)
            sys.exit(1)
        props[d[0]] = d[1]

    miyadaiku.core.DEBUG = args.debug

    d = pathlib.Path(args.directory)
    site = Site(d, props)

    site.pre_build()
    site.build()


def main():
    _main()


if __name__ == '__main__':
    main()
