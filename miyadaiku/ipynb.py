from typing import Dict, Any, Tuple, List, Optional
import copy
import re
from nbconvert.exporters import HTMLExporter
import nbformat
from bs4 import BeautifulSoup
from miyadaiku import ContentSrc
from . import parsesrc


def _export(json: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    config = {"TemplateExporter": {"template_file": "basic.tpl"}}
    html, _ = HTMLExporter(config).from_notebook_node(json)

    metadata = {"type": "article"}
    metadata.update(json.get("metadata", {}).get("miyadaiku", {}))

    return metadata, html


def _load_string(s: str) -> Tuple[Dict[str, Any], str]:
    json = nbformat.reads(s, nbformat.current_nbformat)
    return _export(json)


def get_cellfilename(cell: Dict[str, Any]) -> Optional[str]:
    if cell.get("cell_type", "") == "markdown":
        src = cell.get("source", "")
        m = parsesrc.SEP.match(src)
        if m:
            cell["source"] = src[m.end() :]
            return m[1].strip()
    return None


def split_cells(
    src: ContentSrc, cells: List[Dict[str, Any]]
) -> List[Tuple[ContentSrc, List[Dict[str, Any]]]]:
    if not cells:
        return [(src, cells)]

    cell = cells[0]
    filename = get_cellfilename(cell)
    if not filename:
        return [(src, cells)]

    ret = [(src.copy()._replace(contentpath=(src.contentpath[0], filename)), [cell])]

    for cell in cells[1:]:
        filename = get_cellfilename(cell)
        if not filename:
            ret[-1][-1].append(cell)
        else:
            subsrc = src.copy()._replace(contentpath=(src.contentpath[0], filename))
            ret.append((subsrc, [cell]))

    return ret


def load(src: ContentSrc) -> List[Tuple[ContentSrc, str]]:
    s = src.read_text()
    json = nbformat.reads(s, nbformat.current_nbformat)

    cells = split_cells(src, json.get("cells", []))
    ret = []
    for subsrc, subcells in cells:
        subjson = copy.deepcopy(json)
        cellmeta: Dict[str, Any] = {}
        if subcells:
            top = subcells[0]
            if top.get("cell_type", "") == "markdown":
                srcstr = top.get("source", "")
                if srcstr:
                    cellmeta, srcstr = parsesrc.split_yaml(srcstr, "---")
                    top["source"] = srcstr

        subjson["cells"] = subcells

        meta, html = _export(subjson)
        meta.update(cellmeta)

        subsrc.metadata.update(meta)
        ret.append((subsrc, html))

    return ret
