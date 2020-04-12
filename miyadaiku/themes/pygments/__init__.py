import pkg_resources
import posixpath
from miyadaiku import site

DEST_PATH = "/static/pygments/"


def load_package(site: site.Site) -> None:
    cssname = site.config.get("/", "pygments_css")
    css_path = posixpath.join(DEST_PATH, cssname)
    site.config.add("/", {"pygments_css_path": css_path})

    src_path = "externals/" + cssname
    csscontent = pkg_resources.resource_string(__name__, src_path)

    site.files.add_bytes("binary", css_path, csscontent)

    site.add_template_module("pygments", "miyadaiku.themes.pygments!macros.html")
