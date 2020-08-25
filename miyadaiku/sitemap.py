from __future__ import annotations

import xml.etree.cElementTree as ET
from typing import TYPE_CHECKING, Sequence

from miyadaiku import SITEMAP_CHANGEFREQ, SITEMAP_FILENAME, OutputInfo

if TYPE_CHECKING:
    from .site import Site


def write_sitemap(site: Site, outputinfos: Sequence[OutputInfo]) -> None:
    root = ET.Element("urlset")
    root.attrib["xmlns"] = "http://www.sitemaps.org/schemas/sitemap/0.9"

    for oi in outputinfos:
        if not oi.sitemap:
            continue

        url = ET.SubElement(root, "url")
        ET.SubElement(url, "loc").text = oi.url

        date = oi.updated or oi.date
        if date:
            ET.SubElement(url, "lastmod").text = date.isoformat()
        ET.SubElement(url, "changefreq").text = SITEMAP_CHANGEFREQ

        ET.SubElement(url, "priority").text = str(oi.sitemap_priority)

    tree = ET.ElementTree(root)
    tree.write(
        site.outputdir / SITEMAP_FILENAME, encoding="utf-8", xml_declaration=True
    )
