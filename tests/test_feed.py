from conftest import SiteRoot
import datetime
import xml.etree.ElementTree as ET


def test_feed(siteroot: SiteRoot) -> None:
    for i in range(21):
        tag = f"tag{i % 2 + 1}"
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
