from pathlib import Path
from miyadaiku import rst
from miyadaiku import ContentSrc


def to_contentsrc(path: Path) -> ContentSrc:
    return ContentSrc("", str(path), {}, ((), ""))


def test_load(sitedir: Path) -> None:
    f = sitedir / "test1.rst"
    f.write_text(
        """
:jinja:`{}`

.. code-block:: html
   :caption: caption

   :jinja:`{{}}`
    """
    )

    metadata, text = rst.load(to_contentsrc(f))
    assert (
        text.strip()
        == """<p>{}</p>

<div class="code-block">
<div class="code-block-caption">caption</div>
<div class="highlight"><pre><span></span>:jinja:`&#123;&#123;&#125;&#125;`
</pre></div>

</div>"""
    )


def test_load2(sitedir: Path) -> None:
    f = sitedir / "file1.rst"
    f.write_text(
        """
..  {{ page.site_title }} --

"""
    )

    metadata, text = rst.load(to_contentsrc(f))
    assert text == "<!-- &#123;&#123; page.site_title &#125;&#125; - - -->\n"


def test_articledirective(sitedir: Path) -> None:
    f = sitedir / "file1.rst"
    f.write_text(
        """
.. article::
   :date: 2017-01-01
   :title: title<>

test
"""
    )

    metadata, text = rst.load(to_contentsrc(f))
    assert metadata["date"] == "2017-01-01"
    assert metadata["title"] == "title<>"


def test_jinjadirective(sitedir: Path) -> None:
    f = sitedir / "file1.rst"
    f.write_text(
        """
.. jinja::
   {{<a><b>}}
   <a><b>

:jinja:`{{abc}}`
"""
    )

    metadata, text = rst.load(to_contentsrc(f))
    assert (
        text
        == """{{<a><b>}}
<a><b><p>{{abc}}</p>
"""
    )


def test_xref(sitedir: Path) -> None:
    f = sitedir / "file1.rst"
    f.write_text(
        """
.. target:: anchor-name
"""
    )
    metadata, text = rst.load(to_contentsrc(f))
    print(text)
    assert text == """<div class="header_target" id="anchor-name"></div>"""


def test_title(sitedir: Path) -> None:
    f = sitedir / "file1.rst"
    f.write_text(
        """
title1 http://example.com
-----------------------------

abc
"""
    )
    metadata, text = rst.load(to_contentsrc(f))
    assert metadata["title"] == "title1 http://example.com"


def test_subtitle(sitedir: Path) -> None:
    f = sitedir / "file1.rst"
    f.write_text(
        """
title1
--------------

title2
===========

abc
"""
    )
    metadata, text = rst.load(to_contentsrc(f))
    print(text)
    assert "title1" not in text
    assert "<h1>title2</h1>" in text


def test_pygments(sitedir: Path) -> None:
    f = sitedir / "file1.rst"
    f.write_text(
        """

.. code-block:: html
   :caption: caption
   :linenos:

   :jinja:`{{}}`
"""
    )
    metadata, text = rst.load(to_contentsrc(f))
    print(text)
    assert (
        text.strip()
        == """<div class="code-block">
<div class="code-block-caption">caption</div>
<table class="highlighttable"><tr><td class="linenos"><div class="linenodiv"><pre>1</pre></div></td><td class="code"><div class="highlight"><pre><span></span>:jinja:`&#123;&#123;&#125;&#125;`
</pre></div>
</td></tr></table>
</div>"""  # noqa
    )
