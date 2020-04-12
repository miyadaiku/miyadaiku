import pkg_resources
from nbconvert.exporters import HTMLExporter
import nbformat
from bs4 import BeautifulSoup, Doctype
import markupsafe

from miyadaiku import site

EMPTY_IPYNB = "empty.ipynb"

def _build_head() -> str:
    src = pkg_resources.resource_string("miyadaiku.themes.ipynb", EMPTY_IPYNB)
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
            if "charset" in x.attrs:
                x.extract()

    return str(soup)


def load_package(site:site.Site)->None:
    css = _build_head()

    site.files.add_bytes("binary", "/static/ipynb/ipynb.css", css.encode('utf-8'))
 
    site.add_jinja_global("IPYNB_CSS", markupsafe.Markup(css))
    site.add_template_module(
        "ipynb", "miyadaiku.themes.ipynb!macros.html"
    )
