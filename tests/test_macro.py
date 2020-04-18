from conftest import create_contexts, SiteRoot


def test_ga(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "index.rst",
                """
title
----------------
.. jinja::

   {{ macros.google_analytics() }}
""",
            )
        ],
    )

    ctx.site.config.add("/", {"ga_tracking_id": "12345"})
    (output,) = ctx.build()

    assert "ga('create', '12345', 'auto')" in output.read_text()


def test_image(siteroot: SiteRoot) -> None:

    siteroot.write_text(siteroot.contents / "img/img.png", "")
    siteroot.write_text(
        siteroot.contents / "index.rst",
        """
.. jinja::

   {{ macros.image(page.load('/img/img.png')) }}
""",
    )

    site = siteroot.load({}, {})
    site.build()

    ret = (siteroot.outputs / "index.html").read_text()
    assert "img/img.png" in ret


def test_og(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.templates / "page_article.html",
        """
{{ macros.opengraph(page) }}
""",
    )

    siteroot.write_text(siteroot.contents / "img/img.png", "")
    siteroot.write_text(
        siteroot.contents / "index.rst",
        """
.. article::
   :og_image: /img/img.png

test article
------------------

body

""",
    )

    site = siteroot.load({}, {})
    site.build()

    ret = (siteroot.outputs / "index.html").read_text()
    assert 'content="http://localhost:8888/img/img.png"' in ret
