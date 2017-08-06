from pathlib import Path
from miyadaiku.core import html
import datetime


def test_load(sitedir):
    sitedir.joinpath('a.html').write_text('''
title: title
tags: a,b,c
draft: false
date: 2017-1-1

<a>
''')

    metadata, text = html .load(sitedir.joinpath('a.html'))

    assert metadata['title'] == 'title'

    assert text == '<a>'
