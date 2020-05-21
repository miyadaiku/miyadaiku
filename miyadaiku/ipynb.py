from typing import Dict, Any, Tuple
import re
from nbconvert.exporters import HTMLExporter
import nbformat
from bs4 import BeautifulSoup
from miyadaiku import ContentSrc


def _export(json: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    config = {"TemplateExporter": {"template_file": "basic.tpl"}}
    html, _ = HTMLExporter(config).from_notebook_node(json)

    metadata = {"type": "article"}
    metadata.update(json.get("metadata", {}).get("miyadaiku", {}))

    return metadata, "<div>" + html + "</div>"


def load(src: ContentSrc) -> Tuple[Dict[str, Any], str]:
    if src.package:
        s = src.read_text()
        return load_string(s)
    else:
        json = nbformat.read(src.srcpath, nbformat.current_nbformat)
        return _export(json)


def load_string(s: str) -> Tuple[Dict[str, Any], str]:
    json = nbformat.reads(s, nbformat.current_nbformat)
    return _export(json)
