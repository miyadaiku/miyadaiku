from conftest import create_contexts, SiteRoot


def test_load(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc1.rst",
                """
:jinja:`{}`

.. code-block:: html
   :caption: caption

   :jinja:`{{}}`
    """,
            )
        ],
    )

    assert ctx.content.body
    assert (
        ctx.content.body.strip()
        == b"""<p>{}</p>

<div class="code-block">
<div class="code-block-caption">caption</div>
<div class="highlight"><pre><span></span>:jinja:`&#123;&#123;&#125;&#125;`
</pre></div>

</div>"""
    )


def test_load2(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc1.rst",
                """
..  {{ page.site_title }} --

""",
            )
        ],
    )

    assert ctx.content.body
    assert (
        ctx.content.body.strip()
        == b"<!-- &#123;&#123; page.site_title &#125;&#125; - - -->"
    )


def test_articledirective(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc1.rst",
                """
.. article::
   :date: 2017-01-01
   :title: title<>

test
""",
            )
        ],
    )

    metadata = ctx.content.src.metadata
    assert metadata["date"] == "2017-01-01"
    assert metadata["title"] == "title<>"


def test_jinjadirective(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc1.rst",
                """
.. jinja::
   {{<a><b>}}
   <a><b>

:jinja:`{{abc}}`
""",
            )
        ],
    )

    assert ctx.content.body == (
        b"""{{<a><b>}}
<a><b><p>{{abc}}</p>
"""
    )


def test_xref(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc1.rst",
                """
.. target:: anchor-name
""",
            )
        ],
    )
    assert ctx.content.body == b"""<div class="header_target" id="anchor-name"></div>"""


def test_title(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc1.rst",
                """
title1 http://example.com
-----------------------------

abc
""",
            )
        ],
    )

    assert ctx.content.src.metadata["title"] == "title1 http://example.com"


def test_subtitle(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc1.rst",
                """
title1
--------------

title2
===========

abc
""",
            )
        ],
    )
    text = str(ctx.content.body)
    assert "title1" not in text
    assert "<h1>title2</h1>" in text


def test_pygments(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc1.rst",
                """

.. code-block:: html
   :caption: caption
   :linenos:

   :jinja:`{{}}`
""",
            )
        ],
    )

    assert ctx.content.body
    assert ctx.content.body.strip() == (
        b"""<div class="code-block">
<div class="code-block-caption">caption</div>
<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv">"""
        b"""<pre>1</pre></div></td><td class="code"><div class="highlight"><pre><span></span>:jinja:`&#123;&#123;&#125;&#125;`
</pre></div>
</td></tr></table>
</div>"""
    )
