from pathlib import Path
from miyadaiku.core import md
import datetime


def test_load(sitedir):  # NOQA
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
    assert metadata['tags'] == ['a', 'b', 'c']
    assert metadata['date'] == datetime.datetime(2017, 1, 1)


def test_load2(sitedir):  # NOQA
    (sitedir / 'a.md').write_text('''a :jinja:`{{abc}}` b''')

    metadata, text = md.load(sitedir/'a.md')
    assert text == '<p>a {{abc}} b</p>'

    (sitedir / 'a.md').write_text('''
:jinja:`{{abc
def}}`
''')

    metadata, text = md.load(sitedir/'a.md')
    assert text == '''{{abc
def}}'''


