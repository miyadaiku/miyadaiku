import posixpath
from typing import cast

import importlib_resources

from miyadaiku import site

DEST_PATH = "/static/pygments/"


def get_css(style: str) -> str:
    from pygments.formatters import get_formatter_by_name

    fmter = get_formatter_by_name("html", style=style)
    return cast(str, fmter.get_style_defs(".highlight"))


def load_package(site: site.Site) -> None:
    cssname = site.config.get("/", "pygments_css", None)
    if cssname:
        css_path = posixpath.join(DEST_PATH, cssname)
        site.config.add("/", {"pygments_css_path": css_path})

        src_path = "externals/" + cssname
        path = importlib_resources.files(__name__).joinpath(src_path)  # type: ignore
        csscontent = path.read_bytes()
        site.files.add_bytes("binary", css_path, csscontent)
    else:
        stylename = site.config.get("/", "pygments_style")
        csscontent = get_css(stylename).encode("utf-8")

        css_path = posixpath.join(DEST_PATH, stylename + ".css")
        site.files.add_bytes("binary", css_path, csscontent)

        site.config.add("/", {"pygments_css_path": css_path})

    site.add_template_module("pygments", "miyadaiku.themes.pygments!macros.html")
