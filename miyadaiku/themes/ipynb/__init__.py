import importlib_resources
from bs4 import BeautifulSoup, Doctype
import markupsafe

from miyadaiku import site

EMPTY_IPYNB = "empty.ipynb"

css_mathjax = """
<!-- Load mathjax -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/latest.js?config=TeX-AMS_HTML"></script>
    <!-- MathJax configuration -->
    <script type="text/x-mathjax-config">
    MathJax.Hub.Config({
        tex2jax: {
            inlineMath: [ ['$','$'], ["\\(","\\)"] ],
            displayMath: [ ['$$','$$'], ["\\[","\\]"] ],
            processEscapes: true,
            processEnvironments: true
        },
        // Center justify equations in code and markdown cells. Elsewhere
        // we use CSS to left justify single line equations in code cells.
        displayAlign: 'center',
        "HTML-CSS": {
            styles: {'.MathJax_Display': {"margin": 0}},
            linebreaks: { automatic: true }
        }
    });
    </script>
    <!-- End of mathjax configuration --><
"""


def _build_head() -> str:
    from nbconvert.exporters import HTMLExporter
    import nbformat

    src = (
        importlib_resources.files("miyadaiku.themes.ipynb") / EMPTY_IPYNB
    ).read_bytes()
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


def load_package(site: site.Site) -> None:
    css = _build_head()

    site.files.add_bytes("binary", "/static/ipynb/ipynb.css", css.encode("utf-8"))

    site.add_jinja_global("IPYNB_CSS", markupsafe.Markup(css))
    site.add_template_module("ipynb", "miyadaiku.themes.ipynb!macros.html")
