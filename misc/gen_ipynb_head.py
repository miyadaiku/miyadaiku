from pathlib import Path
from nbconvert.exporters import HTMLExporter
import nbformat
from bs4 import BeautifulSoup



ipynb = Path(__file__).parent / 'empty.ipynb'
json = nbformat.read(str(ipynb), nbformat.current_nbformat)
html, _ = HTMLExporter({}).from_notebook_node(json)
soup = BeautifulSoup(html, "html.parser")

soup.head.title.extract()

print("{% macro set_header() -%}")
print(soup.head)
print("{%- endmacro %}")
