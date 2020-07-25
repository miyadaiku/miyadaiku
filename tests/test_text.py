from pathlib import Path
from miyadaiku import text

from conftest import to_contentsrc


def test_meta(sitedir: Path) -> None:
    sitedir.joinpath("a.txt").write_text(
        """---
title: title<>
---

adfas
:jinja:`{{ancdef}}`

<>
"""
    )

    ((src, txt),) = text.load(to_contentsrc(sitedir / "a.txt"))
    assert src.metadata["ext"] == ".txt"
    assert src.metadata["article_template"] == "plain.txt"
    assert src.metadata["type"] == "article"
    assert src.metadata["title"] == "title<>"


def test_split(sitedir: Path) -> None:
    sitedir.joinpath("a.txt").write_text(
        """%%%% b.txt
first"""
    )

    ((src, txt),) = text.load(to_contentsrc(sitedir / "a.txt"))

    assert src.metadata["type"] == "article"
    assert src.contentpath == ((), "b.txt")
    assert txt == "first"

    sitedir.joinpath("a.txt").write_text(
        """%%%% b.txt
---
tags:
  - a
  - b
  - c
---
first
%%%% c.txt
second"""
    )

    ((src1, text1), (src2, text2),) = text.load(to_contentsrc(sitedir / "a.txt"))

    assert src1.metadata["type"] == "article"
    assert src1.contentpath == ((), "b.txt")
    assert src1.metadata["tags"] == ["a", "b", "c"]
    assert text1 == "first\n"

    assert src2.metadata["type"] == "article"
    assert src2.contentpath == ((), "c.txt")
    assert text2 == "second"
