from pathlib import Path
from miyadaiku.core import md
import datetime


def test_meta(sitedir):
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


def test_inline(sitedir):
    (sitedir / 'a.md').write_text('''a :jinja:`{{abc}}` b''')

    metadata, text = md.load(sitedir / 'a.md')
    assert text == '<p>a {{abc}} b</p>'


def test_multiline(sitedir):
    (sitedir / 'a.md').write_text('''
:jinja:`{{abc
def}}`
''')
    metadata, text = md.load(sitedir / 'a.md')
    assert text == '''{{abc
def}}'''


def test_esc(sitedir):
    (sitedir / 'a.md').write_text('''
\:jinja:`{{abcdef}}`
''')
    metadata, text = md.load(sitedir / 'a.md')
    print(text)


def test_fence(sitedir):
    (sitedir / 'a.md').write_text('''

```
:jinja:`{{abcdef}}`
```
''')

    metadata, text = md.load(sitedir / 'a.md')
    print(text)
    assert text == '''<div class="codehilite"><pre><span></span>{{abcdef}}
</pre></div>'''


def test_code(sitedir):
    (sitedir / 'a.md').write_text('''

    :jinja:`{{abcdef}}`
''')
    metadata, text = md.load(sitedir / 'a.md')
    assert text == '''<div class="codehilite"><pre><span></span>{{abcdef}}
</pre></div>'''


def test_target(sitedir):
    (sitedir / 'a.md').write_text('''
.. target:: abcdefg
''')
    metadata, text = md.load(sitedir / 'a.md')
    assert text == '''<div class="header_target" id="abcdefg"></div>'''
