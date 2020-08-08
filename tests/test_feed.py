from typing import cast
from conftest import SiteRoot
import datetime
import xml.etree.ElementTree as ET


def test_feed(siteroot: SiteRoot) -> None:
    for i in range(21):
        tag = f"tag{(i % 4) + 1}"
        d = datetime.datetime(2020, 1, 1) + datetime.timedelta(days=i)
        siteroot.write_text(
            siteroot.contents / f"htmldir/{i}.html",
            f"""
date: {d.ctime()}

tags: {tag}

html{i} - tag: {tag}
""",
        )

    siteroot.write_text(
        siteroot.contents / "feed.yml",
        """
type: feed
""",
    )

    site = siteroot.load({}, {})
    site.build()

    src = (site.root / "outputs/feed.xml").read_text()
    root = ET.fromstring(src)

    entries = root.findall("./{http://www.w3.org/2005/Atom}entry")
    assert len(entries) == 20

    siteroot.write_text(
        siteroot.contents / "feed.yml",
        """
type: feed
filters:
    tags: ['tag1', 'tag2']
""",
    )

    site = siteroot.load({}, {})
    site.build()

    src = (site.root / "outputs/feed.xml").read_text()
    root = ET.fromstring(src)

    entries = root.findall("./{http://www.w3.org/2005/Atom}entry")
    assert len(entries) == 11

    siteroot.write_text(
        siteroot.contents / "feed.yml",
        """
type: feed
excludes:
    tags: ['tag1', 'tag2']
""",
    )

    site = siteroot.load({}, {})
    site.build()

    src = (site.root / "outputs/feed.xml").read_text()
    root = ET.fromstring(src)

    entries = root.findall("./{http://www.w3.org/2005/Atom}entry")
    assert len(entries) == 10


def test_feed_dir(siteroot: SiteRoot) -> None:
    d = datetime.datetime(2020, 1, 1)
    siteroot.write_text(
        siteroot.contents / "dir1" / "doc1.html",
        f"""---
date: {d.ctime()}
---
body
""",
    )

    siteroot.write_text(
        siteroot.contents / "dir2" / "doc2.html",
        f"""---
date: {d.ctime()}
---
body
""",
    )

    siteroot.write_text(
        siteroot.contents / "feed.yml",
        """
type: feed
directories:
   - dir1
""",
    )

    site = siteroot.load({}, {})
    site.build()

    src = (site.root / "outputs/feed.xml").read_text()
    root = ET.fromstring(src)

    entries = root.findall("./{http://www.w3.org/2005/Atom}entry")
    assert len(entries) == 1

    link = entries[0].find("{http://www.w3.org/2005/Atom}link")
    assert "/dir1/doc1.html" in cast(str, link.get("href"))
