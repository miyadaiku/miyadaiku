from conftest import SiteRoot


def test_theme_pygments(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "index.rst",
        """
title
----------------
.. jinja::
   {{ pygments.load_css(page) }}
""",
    )

    site = siteroot.load({"themes": ["miyadaiku.themes.pygments"]}, {})
    site.build()

    s = (siteroot.outputs / "index.html").read_text()

    assert '<link href="static/pygments/native.css" rel="stylesheet"/>' in s
    assert (siteroot.outputs / "static/pygments/native.css").exists()


def test_theme_pygments_cssname(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "index.rst",
        """
title
----------------
.. jinja::
   {{ pygments.load_css(page) }}
""",
    )

    site = siteroot.load(
        {"themes": ["miyadaiku.themes.pygments"]},
        {"pygments_css": "pygments_friendly.css"},
    )
    site.build()

    s = (siteroot.outputs / "index.html").read_text()

    assert '<link href="static/pygments/pygments_friendly.css" rel="stylesheet"/>' in s
    assert (siteroot.outputs / "static/pygments/pygments_friendly.css").exists()
