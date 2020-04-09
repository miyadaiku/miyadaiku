from pathlib import Path
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

    metadata, text = html.load(sitedir.joinpath("a.html"))

    assert metadata["title"] == "title<>"

    assert text == "<a>"
