from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, output, main

def test_macro(sitedir):
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
    site.write()

    ret = sitedir.joinpath('outputs/index.html').read_text()
    assert "ga('create', '12345', 'auto')" in ret
