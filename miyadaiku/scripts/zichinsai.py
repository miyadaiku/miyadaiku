import argparse
import locale
import pathlib
import sys

import tzlocal

from miyadaiku import CONTENTS_DIR, FILES_DIR, TEMPLATES_DIR, __version__

locale.setlocale(locale.LC_ALL, "")

parser = argparse.ArgumentParser(description="Start new miyadaiku document.")
parser.add_argument(
    "--overwrite",
    "-o",
    action="store_true",
    default=False,
    help="Overwrite target directory",
)
parser.add_argument("directory", help="directory name")
parser.add_argument("--version", "-v", action="version", version=f"{__version__}")


src = """---
title: sample document
---

Hello world.

"""


def main() -> None:
    args = parser.parse_args()

    d = pathlib.Path(args.directory)
    if d.exists():
        if not args.overwrite:
            print(
                f"{str(d)!r} already exists. Use --overwrite to overwrite.",
                file=sys.stderr,
            )
            sys.exit(1)

    tz = tzlocal.get_localzone().zone

    locale.setlocale(locale.LC_ALL, "")
    lang = locale.getlocale()[0]
    lang = (lang or "en-US").replace("_", "-")
    charset = "utf-8"

    (d / CONTENTS_DIR).mkdir(parents=True)
    (d / FILES_DIR).mkdir()
    (d / TEMPLATES_DIR).mkdir()

    yaml = f"""# Miyadaiku config file

# Base URL of the site
site_url: http://localhost:8888/

# Title of the site
site_title: FIXME - site title

# Default language code
lang: {lang}

# Default charset
charset: {charset}

# Default timezone
timezone: {tz}

# List of site theme
# themes:
#   - miyadaiku.themes.sample.blog

"""

    (d / "config.yml").write_text(yaml, "utf-8")
    (d / CONTENTS_DIR / "index.md").write_text(src, "utf-8")


if __name__ == "__main__":
    main()
