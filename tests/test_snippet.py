from conftest import SiteRoot


def test_load(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "doc1.html",
        """
type: snippet

snipet<b>text</b>
""",
    )

    siteroot.write_text(
        siteroot.contents / "doc2.html",
        """
title: title

{{ page.load("./doc1.html").html }}

""",
    )

    site = siteroot.load({}, {})
    site.build()

    assert len(list(siteroot.outputs.iterdir())) == 1
    text = (siteroot.outputs / "doc2.html").read_text()
    assert "snipet<b>text</b>" in text
