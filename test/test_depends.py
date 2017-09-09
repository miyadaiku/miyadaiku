from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, main
import yaml


def test_build_depend(sitedir):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''
.. jinja::

   {{ page.load('./a.rst').html }}

''')

    content.joinpath('a.rst').write_text('''

heh
''')

    site = main.Site(sitedir)
    err = site.build()
    err
#    assert deps[((), 'index.rst')] == [('index.html', ((), 'index.rst'))]
#    assert sorted(deps[((), 'a.rst')]) == sorted(
#        [('index.html', ((), 'index.rst')), ('a.html', ((), 'a.rst'))])
