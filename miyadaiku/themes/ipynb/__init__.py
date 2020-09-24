import importlib_resources
import markupsafe
from bs4 import BeautifulSoup, Doctype

from miyadaiku import site

EMPTY_IPYNB = "empty.ipynb"


def _build_head() -> str:
    import nbformat
    from nbconvert.exporters import HTMLExporter

    path = importlib_resources.files("miyadaiku.themes.ipynb") / EMPTY_IPYNB  # type: ignore
    src = path.read_bytes()
    json = nbformat.reads(src, nbformat.current_nbformat)

    html, _ = HTMLExporter({}).from_notebook_node(json)
    soup = BeautifulSoup(html, "html.parser")

    soup.head.title.extract()
    soup.body.extract()

    soup.head.unwrap()
    soup.html.unwrap()

    for x in soup.children:
        if isinstance(x, Doctype):
            x.extract()
        if x.name == "meta":
            x.extract()

    return str(soup)


def load_package(site: site.Site) -> None:
    css = _build_head()

    site.files.add_bytes("binary", "/static/ipynb/ipynb.css", css.encode("utf-8"))

    site.add_jinja_global("IPYNB_CSS", markupsafe.Markup(css))
    site.add_template_module("ipynb", "miyadaiku.themes.ipynb!macros.html")
