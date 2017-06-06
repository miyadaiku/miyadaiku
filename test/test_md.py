from pathlib import Path
from miyadaiku.core import md
from testutil import sitedir
import datetime


def test_load(sitedir):
    sitedir.joinpath('a.md').write_text('''
title: title
tags: a,b,c
draft: false
date: 2017-1-1	

adfas
:jinja:`{{ancdef}}`

{}
''')

    metadata, text = md .load(sitedir.joinpath('a.md'))

    assert metadata['type'] == 'article'
    assert metadata['title'] == 'title'
    assert metadata['draft'] is False
    assert metadata['tags'] == ['a','b','c']
    assert metadata['date'] == datetime.datetime(2017, 1,1)
