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


def test_markupsafe(sitedir):
    (sitedir / 'contents/test.yml').write_text("""
type: article
html: "<abc> "
abstract: "<def>"
""")

    (sitedir / 'contents/disp.rst').write_text("""

.. jinja::

   {{page.load('./test.yml').html}}


.. jinja::

   {{page.load('./test.yml').abstract}}


""")

    import miyadaiku.core
    site = main.Site(sitedir)
    site.build()

    p = (sitedir.joinpath('outputs') / 'disp.html').read_text()
    assert """<abc>""" in p
    assert """<def>""" in p


def test_exception_tag(sitedir):
    (sitedir / 'contents/test.rst').write_text("""
.. jinja::

   {{1/0}}

""")

    site = main.Site(sitedir)
    site.build()

    # todo: check output


def test_exception_templ(sitedir):
    (sitedir / 'contents/test.rst').write_text("""
abc
""")

    (sitedir / 'templates/page_article.html').write_text("""

{{1/0}}

{{page.html}}
""")

    site = main.Site(sitedir, debug=True)
    site.build()

    # todo: check output
