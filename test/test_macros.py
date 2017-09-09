from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, main


def test_ga(sitedir):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''
title
----------------
.. jinja::

   {{ macros.google_analytics() }}
''')

    site = main.Site(sitedir)
    site.config.add('/', {'ga_tracking_id': '12345'})
    site.build()

    ret = sitedir.joinpath('outputs/index.html').read_text()
    assert "ga('create', '12345', 'auto')" in ret


def test_image(sitedir):
    (sitedir / 'contents/img').mkdir()
    (sitedir / 'contents/img/img.png').write_text('')
    (sitedir / 'contents/index.rst').write_text('''
.. jinja::

   {{ macros.image(page.load('/img/img.png')) }}
''')

    site = main.Site(sitedir)
    site.build()

    ret = sitedir.joinpath('outputs/index.html').read_text()
    assert 'img/img.png' in ret


def test_og(sitedir):
    (sitedir / 'templates/page_article.html').write_text('''
{{ macros.opengraph(page) }}
''')

    (sitedir / 'contents/img').mkdir()
    (sitedir / 'contents/img/img.png').write_text('')
    (sitedir / 'contents/index.rst').write_text('''

.. article::
   :og_image: /img/img.png

test article
------------------

body

''')

    site = main.Site(sitedir)
    site.build()

    ret = sitedir.joinpath('outputs/index.html').read_text()
    print(ret)
    assert 'content="http://localhost:8888/img/img.png"' in ret
