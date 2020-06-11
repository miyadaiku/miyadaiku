from pathlib import Path
from miyadaiku import ContentSrc, md

from conftest import to_contentsrc


def test_meta(sitedir: Path) -> None:
    sitedir.joinpath("a.md").write_text(
        """
title: title<>
tags: a,b,c
draft: false
date: 2017-1-1

adfas
:jinja:`{{ancdef}}`

{}
"""
    )

    ((src, text),) = md.load(to_contentsrc(sitedir / "a.md"))

    assert src.metadata["type"] == "article"
    assert src.metadata["title"] == "title<>"


def test_inline(sitedir: Path) -> None:
    (sitedir / "a.md").write_text("""a :jinja:`{{abc}}` b""")

    ((src, text),) = md.load(to_contentsrc(sitedir / "a.md"))
    assert text == "<p>a {{abc}} b</p>"


def test_multiline(sitedir: Path) -> None:
    (sitedir / "a.md").write_text(
        """
:jinja:`{{abc
def}}`
"""
    )
    ((src, text),) = md.load(to_contentsrc(sitedir / "a.md"))
    assert (
        text
        == """{{abc
def}}"""
    )


def test_esc(sitedir: Path) -> None:
    (sitedir / "a.md").write_text(
        """
:jinja:`{{abcdef}}`
"""
    )
    ((src, text),) = md.load(to_contentsrc(sitedir / "a.md"))
    print(text)
    assert text == "{{abcdef}}"


def test_fence1(sitedir: Path) -> None:
    (sitedir / "a.md").write_text(
        """

```
:jinja:`{{abcdef}}`
```
"""
    )

    ((src, text),) = md.load(to_contentsrc(sitedir / "a.md"))
    print(text)
    assert (
        text
        == """<div class="highlight"><pre><span></span><code>{{abcdef}}
</code></pre></div>"""
    )


def test_fence2(sitedir: Path) -> None:
    (sitedir / "a.md").write_text(
        """

```python
{1:1}
```
"""
    )

    ((src, text),) = md.load(to_contentsrc(sitedir / "a.md"))
    print(text)
    assert (
        """&#123;</span><span class="mi">1</span><span class="p">:</span><span class="mi">1</span><span class="p">&#125;"""
        in text
    )


def test_code(sitedir: Path) -> None:
    (sitedir / "a.md").write_text(
        """

    :jinja:`{{abcdef}}`
"""
    )
    ((src, text),) = md.load(to_contentsrc(sitedir / "a.md"))
    assert (
        text
        == """<div class="highlight"><pre><span></span><code>{{abcdef}}
</code></pre></div>"""
    )


def test_target(sitedir: Path) -> None:
    (sitedir / "a.md").write_text(
        """
.. target:: abcdefg

hello
"""
    )
    ((src, text),) = md.load(to_contentsrc(sitedir / "a.md"))
    assert (
        text
        == """<div class="header_target" id="abcdefg"></div>
<p>hello</p>"""
    )
