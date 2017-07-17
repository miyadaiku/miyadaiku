import re
import pytest
import pathlib
from miyadaiku.core import main

def test_feed(sitedir): # NOQA
    sitedir.joinpath('config.yml').write_text('')

    content = sitedir / 'contents'
    content.joinpath('test.rst').write_text("""

.. jinja::

   {{ macros.image(page, page, alt='<>a"\lt', link=page.path_to(page)) }}

""")

    site = main.Site(sitedir)
    site.build()
    site.write()

    p = sitedir.joinpath('outputs') / 'test.html'
    print(p.read_text())

