from pathlib import Path
from miyadaiku import md


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

    metadata, text = md.load(sitedir / "a.md")

    assert metadata["type"] == "article"
    assert metadata["title"] == "title<>"


def test_inline(sitedir: Path) -> None:
    (sitedir / "a.md").write_text("""a :jinja:`{{abc}}` b""")

    metadata, text = md.load(sitedir / "a.md")
    assert text == "<p>a {{abc}} b</p>"


def test_multiline(sitedir: Path) -> None:
    (sitedir / "a.md").write_text(
        """
:jinja:`{{abc
def}}`
"""
    )
    metadata, text = md.load(sitedir / "a.md")
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
    metadata, text = md.load(sitedir / "a.md")
    print(text)


def test_fence(sitedir: Path) -> None:
    (sitedir / "a.md").write_text(
        """

```
:jinja:`{{abcdef}}`
```
"""
    )

    metadata, text = md.load(sitedir / "a.md")
    print(text)
    assert (
        text
        == """<div class="codehilite"><pre><span></span><code>{{abcdef}}
</code></pre></div>"""
    )


def test_code(sitedir: Path) -> None:
    (sitedir / "a.md").write_text(
        """

    :jinja:`{{abcdef}}`
"""
    )
    metadata, text = md.load(sitedir / "a.md")
    assert (
        text
        == """<div class="codehilite"><pre><span></span><code>{{abcdef}}
</code></pre></div>"""
    )


def test_target(sitedir: Path) -> None:
    (sitedir / "a.md").write_text(
        """
.. target:: abcdefg

hello
"""
    )
    metadata, text = md.load(sitedir / "a.md")
    assert (
        text
        == """<div class="header_target" id="abcdefg"></div>
<p>hello</p>"""
    )
