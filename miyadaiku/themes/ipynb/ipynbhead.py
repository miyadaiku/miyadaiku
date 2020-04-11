import pkg_resources
from nbconvert.exporters import HTMLExporter
import nbformat
from bs4 import BeautifulSoup, Doctype
import markupsafe


EMPTY_IPYNB = "empty.ipynb"

def _build_head()->str:
    src = pkg_resources.resource_string('miyadaiku.themes.ipynb', EMPTY_IPYNB)
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
            if 'charset' in x.attrs:
                x.extract()

    return str(soup)

IPYNB_HEADER = None
def set_header()->str:
    global IPYNB_HEADER
    if not IPYNB_HEADER:
        IPYNB_HEADER = markupsafe.Markup(_build_head())
    return IPYNB_HEADER
