import re
import pytest
import pathlib
from miyadaiku.core import main


def test_feed(sitedir):  # NOQA
    sitedir.joinpath('config.yml').write_text('')

    content = sitedir / 'contents'

    for i in range(20):
        src = '''
.. article::
   :date: 2017-01-01

%d.rst
----------------

article body
:jinja:`{{ page.link_to("./1.rst") }}`
''' % i

        content.joinpath('%i.rst' % i).write_text(src)

    content.joinpath('feed.yml').write_text("""
type: feed
feedtype: rss
""")

    site = main.Site(sitedir)
    site.build()

    p = sitedir.joinpath('outputs') / 'feed.rdf'
    print(p.read_text())
