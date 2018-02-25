from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, main


def test_theme_pygment(sitedir):
    sitedir.joinpath('config.yml').write_text('''

themes:
    - miyadaiku.themes.pygments

''')

    sitedir.joinpath('contents/index.rst').write_text('''
title
----------------
.. jinja::

   {{ pygments.load_css(page) }}
''')

    site = main.Site(sitedir)
    site.build()

    ret = sitedir.joinpath('outputs/index.html').read_text()

    print(ret)
    assert '<link href="static/pygments/pygments_native.css" rel="stylesheet"/>' in ret
    assert (sitedir / 'outputs/static/pygments/pygments_native.css').exists()
