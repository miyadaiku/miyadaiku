import sys
from pathlib import Path
import miyadaiku.site

def build(path):
    site = miyadaiku.site.Site()
    site.load(path, {})
    site.build()


if __name__ == '__main__':
    build(Path(sys.argv[1]))
