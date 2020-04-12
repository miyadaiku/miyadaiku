from conftest import SiteRoot


def test_theme_docutils_html5(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "abc/index.rst",
        """
title
----------------
.. jinja::
   {{ docutils_html5.load_css(page) }}
""",
    )

    site = siteroot.load({"themes": ["miyadaiku.themes.docutils_html5"]}, {})
    site.build()

    s = (siteroot.outputs / "abc/index.html").read_text()

    print(s)

    assert '<link href="../static/docutils_html5/plain.css" rel="stylesheet"/>' in s
    assert '<link href="../static/docutils_html5/minimal.css" rel="stylesheet"/>' in s
    assert (siteroot.outputs / "static/docutils_html5/plain.css").exists()
    assert (siteroot.outputs / "static/docutils_html5/minimal.css").exists()
