import sys
import locale
import argparse
import os
import pathlib
import tzlocal
import happylogging

from miyadaiku.core.main import Site

locale.setlocale(locale.LC_ALL, '')

parser = argparse.ArgumentParser(description='Build miyadaiku project.')
parser.add_argument('directory', help='directory name')
parser.add_argument('--define', '-d', action='append', metavar='property=value',
                    help='Set default property value.')


def main():
    happylogging.initlog(filename='-', level='DEBUG')
    args = parser.parse_args()

    props = {}
    for s in args.define or ():
        d = [p.strip() for p in s.split('=', 1)]
        if len(d) != 2:
            print(f'Invalid property: {s!r}', file=sys.stderr)
            sys.exit(1)
        props[d[0]] = d[1]

    d = pathlib.Path(args.directory)
    site = Site(d, props)

    site.build()
    site.write()


if __name__ == '__main__':
    main()
