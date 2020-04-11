from typing import Dict, Any, Tuple
import re
from pathlib import Path
from nbconvert.exporters import HTMLExporter
import nbformat
from bs4 import BeautifulSoup


def _export(json: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    config = {}#{"TemplateExporter": {"template_file": "basic.tpl"}}
    html, _ = HTMLExporter(config).from_notebook_node(json)


    return soup

def load(path: Path) -> Tuple[Dict[str, Any], str]:
    json = nbformat.read(str(path), nbformat.current_nbformat)
    return _export(json)


ipynb = Path(__file__).parent / 'empty.ipynb'
json = nbformat.read(str(ipynb), nbformat.current_nbformat)
html, _ = HTMLExporter({}).from_notebook_node(json)
soup = BeautifulSoup(html, "html.parser")

soup.head.title.extract()
print(soup.head)
