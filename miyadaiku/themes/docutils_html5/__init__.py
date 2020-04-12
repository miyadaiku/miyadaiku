import pkg_resources
import posixpath
from miyadaiku import site


def load_package(site: site.Site) -> None:
    site.add_template_module(
        "docutils_html5", "miyadaiku.themes.docutils_html5!macros.html"
    )

    minimal_css = pkg_resources.resource_string("docutils.writers.html5_polyglot", "minimal.css")
    plain_css = pkg_resources.resource_string("docutils.writers.html5_polyglot", "plain.css")

    site.files.add_bytes("binary", "/static/docutils_html5/minimal.css", minimal_css)
    site.files.add_bytes("binary", "/static/docutils_html5/plain.css", plain_css)
