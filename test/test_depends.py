from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, builder
from miyadaiku.core.site import Site

import yaml


def build_content(sitedir):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''
.. jinja::

   {{ page.load('./a.rst').html }}

''')

    content.joinpath('a.rst').write_text('''

heh
''')


def test_build_depend(sitedir):
    build_content(sitedir)

    content = sitedir / 'contents'
    site = Site(sitedir)
    site.build()

    deps = builder.Depends(Site(sitedir))

    index_rst = {(key, args) for key, args in deps.depends[((), 'index.rst')]}
    a_rst = {(key, args) for key, args in deps.depends[((), 'a.rst')]}

    assert index_rst == {(((), 'index.rst'), None)}
    assert a_rst == {(((), 'index.rst'), None), (((), 'a.rst'), None)}
    deps.check_rebuild()
    assert not deps.rebuild

    deps.check_content_update()
    assert not site.contents.get_content('/index.rst').updated
    assert not site.contents.get_content('/a.rst').updated

def test_update_article(sitedir):
    build_content(sitedir)
    content = sitedir / 'contents'

    site = Site(sitedir)
    site.build()

    content.joinpath('index.rst').write_text('''

updated

.. jinja::
   {{ page.load('./a.rst').html }}

''')

    newsite = Site(sitedir)
    deps = builder.Depends(newsite)

    deps.check_content_update()
    assert newsite.contents.get_content('/index.rst').updated
    assert not newsite.contents.get_content('/a.rst').updated


def test_update_article_ref(sitedir):

    build_content(sitedir)
    content = sitedir / 'contents'

    site = Site(sitedir)
    site.build()

    content.joinpath('a.rst').write_text('''
heh2
''')

    newsite = Site(sitedir)
    deps = builder.Depends(newsite)

    deps.check_content_update()
    assert newsite.contents.get_content('/index.rst').updated
    assert newsite.contents.get_content('/a.rst').updated


def test_update_propfile(sitedir):
    build_content(sitedir)
    content = sitedir / 'contents'

    site = Site(sitedir)
    site.build()

    content.joinpath('index.rst.props.yml').write_text('''
prop1: prop1vaue
''')

    newsite = Site(sitedir)
    deps = builder.Depends(newsite)

    deps.check_content_update()
    assert newsite.contents.get_content('/index.rst').updated
