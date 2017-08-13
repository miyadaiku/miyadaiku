import re
import pytest
import pathlib
from miyadaiku.core import main


def test_feed(sitedir):  # NOQA
    sitedir.joinpath('config.yml').write_text('')

    content = sitedir / 'contents'
    content.joinpath('test.rst').write_text("""

.. jinja::

   {{ macros.image(page, alt='<>a"\lt', link=page.path_to(page)) }}

""")

    site = main.Site(sitedir)
    site.build()

    p = (sitedir.joinpath('outputs') / 'test.html').read_text()
    assert """<img alt='&lt;&gt;a"\lt' src="test.html"/>""" in p
