from pathlib import Path

from conftest import to_contentsrc

from miyadaiku import html


def test_load(sitedir: Path) -> None:
    sitedir.joinpath("a.html").write_text(
        """
title: title<>
tags: a,b,c
draft: false
date: 2017-1-1

<a>
"""
    )

    ((src, text),) = html.load(to_contentsrc(sitedir.joinpath("a.html")))

    assert src.metadata["title"] == "title<>"
    assert src.metadata["tags"] == "a,b,c"

    assert text == "<a>"


def test_yaml(sitedir: Path) -> None:
    sitedir.joinpath("a.html").write_text(
        """---
title: title<>
tags:
    - a
    - b
    - c
draft: false
date: 2017-1-1
---

<a>
"""
    )

    ((src, text),) = html.load(to_contentsrc(sitedir.joinpath("a.html")))

    assert src.metadata["title"] == "title<>"
    assert src.metadata["tags"] == ["a", "b", "c"]
