import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List

from conftest import SiteRoot
from dateutil import parser

sitemap = "http://www.sitemaps.org/schemas/sitemap/0.9"


def xtmltod(root: ET.Element) -> List[Dict[str, str]]:
    ns = {"sitemap": sitemap}
    urls = root.findall("sitemap:url", ns)

    all = []
    for url in urls:
        d: Dict[str, str] = {}
        for c in url:
            if c.text:
                d[c.tag[len("{" + sitemap + "}") :]] = c.text
        all.append(d)
    return all


def test_update(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "file1.rst",
        """
.. article::
   :date: 2017-01-01
""",
    )
    siteroot.write_text(
        siteroot.contents / "file2.rst",
        """
.. article::
   :updated: 2017-01-02
""",
    )

    siteroot.write_text(siteroot.contents / "image.png", "")

    site = siteroot.load({}, {})
    site.build()

    root = ET.parse(site.outputdir / "sitemap.xml").getroot()

    all = xtmltod(root)
    assert set(d["loc"] for d in all) == {
        "http://localhost:8888/file1.html",
        "http://localhost:8888/file2.html",
    }
    assert set(d["changefreq"] for d in all) == {"daily"}
    assert set(parser.parse(d["lastmod"]) for d in all if "lastmod" in d) == {
        datetime(2017, 1, 1).astimezone(),
        datetime(2017, 1, 2).astimezone(),
    }

    siteroot.write_text(siteroot.contents / "file3.rst", "")
    site = siteroot.load({}, {})
    site.build()
    root = ET.parse(site.outputdir / "sitemap.xml").getroot()

    all = xtmltod(root)
    assert set(d["loc"] for d in all) == {
        "http://localhost:8888/file1.html",
        "http://localhost:8888/file2.html",
        "http://localhost:8888/file3.html",
    }

    siteroot.write_text(
        siteroot.contents / "file2.rst",
        """
.. article::
   :updated: 2017-01-02

update
""",
    )

    site = siteroot.load({}, {})
    site.build()
    root = ET.parse(site.outputdir / "sitemap.xml").getroot()

    all = xtmltod(root)
    assert len(all) == 3
    assert set(d["loc"] for d in all) == {
        "http://localhost:8888/file1.html",
        "http://localhost:8888/file2.html",
        "http://localhost:8888/file3.html",
    }
