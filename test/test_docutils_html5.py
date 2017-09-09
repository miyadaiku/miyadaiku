from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, main


def test_docutils_html5(sitedir):
    sitedir.joinpath('config.yml').write_text('''
themes:
    - miyadaiku.themes.docutils_html5

''')

    sitedir.joinpath('contents/index.rst').write_text('''
title
----------------
.. jinja::

   {{ docutils_html5.load_css(page) }}
''')

    site = main.Site(sitedir)
    site.build()

    ret = sitedir.joinpath('outputs/index.html').read_text()
    assert "minimal.css" in ret
    assert "plain.css" in ret
    assert (sitedir / 'outputs/static/docutils_html5/minimal.css').exists()
    assert (sitedir / 'outputs/static/docutils_html5/plain.css').exists()
