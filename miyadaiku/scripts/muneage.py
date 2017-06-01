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



def main():
    happylogging.initlog(filename='-', level='DEBUG')
    args = parser.parse_args()
    d = pathlib.Path(args.directory)
    site = Site(d)

    site.build()
    site.write()
    

if __name__ == '__main__':
    main()

