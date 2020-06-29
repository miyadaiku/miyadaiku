from conftest import SiteRoot


def test_load(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "doc1.html",
        """
type: snippet

snipet<b>text</b>
{{ page.page_value }}
""",
    )

    siteroot.write_text(
        siteroot.contents / "doc2.html",
        """
title: title

{{ page.set(page_value='aaa') }}
{{ page.load("./doc1.html").html }}

{{ page.set(page_value='bbb') }}
{{ page.load("./doc1.html").html }}

""",
    )

    site = siteroot.load({}, {})
    site.build()

    assert len(list(siteroot.outputs.iterdir())) == 1
    text = (siteroot.outputs / "doc2.html").read_text()
    assert "snipet<b>text</b>" in text
    assert "aaa" in text
    assert "bbb" in text


def test_header(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "doc1.html",
        """
type: snippet

<h1>header-snippet</h1>

""",
    )

    siteroot.write_text(
        siteroot.contents / "doc2.html",
        """
title: title

<h1>header-page</h1>

{{ page.load("./doc1.html").html }}

""",
    )

    site = siteroot.load({}, {})
    site.build()

    assert len(list(siteroot.outputs.iterdir())) == 1
