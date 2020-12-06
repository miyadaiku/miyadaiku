import copy
import hashlib
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import nbformat
from nbconvert.exporters import HTMLExporter
from traitlets.config import Config

from miyadaiku import NBCONVERT_TEMPLATES_DIR, ContentSrc

from . import parsesrc
from .site import Site

options: Optional[Dict[str, Any]] = None
exporters: Dict[Tuple[str, str], HTMLExporter] = {}

root: Optional[Path] = None


def init(site: Site) -> None:
    global options, exporters, root

    options = copy.deepcopy(site.config.get("/", "ipynb_export_options"))
    assert options

    template_name = site.config.get("/", "ipynb_template_name")
    options["TemplateExporter"]["template_name"] = template_name

    template_file = site.config.get("/", "ipynb_template_file")
    options["TemplateExporter"]["template_file"] = template_file

    exporters = {}
    root = site.root / NBCONVERT_TEMPLATES_DIR


def _make_exporter(
    template_name: Optional[str], template_file: Optional[str]
) -> HTMLExporter:

    assert options
    template_name = template_name or options["TemplateExporter"]["template_name"]
    template_file = template_file or options["TemplateExporter"]["template_file"]

    if (template_name, template_file) not in exporters:
        assert options
        assert root

        opt = copy.deepcopy(options)
        opt["TemplateExporter"]["template_name"] = template_name
        opt["TemplateExporter"]["template_file"] = template_file
        opt["TemplateExporter"]["extra_template_basedirs"] = [os.getcwd(), str(root)]

        exp = HTMLExporter(Config(opt))
        exporters[(template_name, template_file)] = exp

    return exporters[(template_name, template_file)]


def _export(
    json: Dict[str, Any],
    template_name: Optional[str] = None,
    template_file: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    assert options

    exp = _make_exporter(template_name, template_file)

    html, _ = exp.from_notebook_node(json)
    metadata = {
        "type": "article",
        "has_jinja": True,
        "loader": "ipynb",
    }
    metadata.update(json.get("metadata", {}).get("miyadaiku", {}))
    return metadata, html


def get_cellfilename(cell: Dict[str, Any]) -> Optional[str]:
    if cell.get("cell_type", "") != "code":
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
            if top.get("cell_type", "") in ("markdown", "raw"):
                srcstr = top.get("source", "")
                if srcstr:
                    cellmeta, srcstr = parsesrc.split_yaml(srcstr, "---")
                    top["source"] = srcstr

        # remove raw cells
        newcells = [c for c in subcells if c.get("cell_type", "") != "raw"]

        jinjatags = {}
        idx = 0

        def conv_jinjatag(s: str) -> str:
            nonlocal idx
            idx += 1
            digest = hashlib.md5(s.encode("utf-8")).hexdigest() + str(idx)
            jinjatags[digest] = s
            return digest

        # save jinja tag
        if cellmeta.get("has_jinja", True):
            for cell in subcells:
                if cell.get("cell_type", "") == "markdown":
                    newsrc = parsesrc.replace_jinjatag(
                        cell.get("source", ""), conv_jinjatag
                    )
                    cell["source"] = newsrc

        # remove empty cells at bottom
        while len(newcells) > 1:
            c = newcells[-1]
            celltype = c.get("cell_type", "")

            if celltype == "markdown":
                if c["source"].strip():
                    break

            elif celltype == "code":
                if c["source"].strip() or c["outputs"]:
                    break

            else:
                break

            # remove cell
            del newcells[-1]

        subjson["cells"] = newcells

        meta, html = _export(
            subjson,
            cellmeta.get("nbconvert_template", None),
            cellmeta.get("nbconvert_templatefile", None),
        )
        meta.update(cellmeta)

        subsrc.metadata.update(meta)

        # restore jinja tag
        html = html.translate({ord("{"): "&#123;", ord("}"): "&#125;"})
        for hash, s in jinjatags.items():
            html = re.sub(rf"(<p>\s*{hash}\s*</p>)|{hash}", s, html, 1)

        ret.append((subsrc, html))

    return ret
