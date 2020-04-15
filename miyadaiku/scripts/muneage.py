import sys
from pathlib import Path
import miyadaiku.site


def main(path: Path) -> None:
    site = miyadaiku.site.Site()
    site.load(path, {})
    site.build()

if __name__ == "__main__":
    main(Path(sys.argv[1]))
