from pathlib import Path
from nbconvert.exporters import HTMLExporter
import nbformat
from bs4 import BeautifulSoup, Doctype


ipynb = Path(__file__).parent / 'empty.ipynb'
json = nbformat.read(str(ipynb), nbformat.current_nbformat)
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

print("{% macro set_header() -%}")
print(soup)
print("{%- endmacro %}")

