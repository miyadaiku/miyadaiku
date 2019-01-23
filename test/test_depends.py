from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, builder
from miyadaiku.core.site import Site

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

    site = Site(sitedir)
    site.build()
    
    deps = builder.Depends(Site(sitedir))

    index_rst = {(key, args) for key, args in deps.depends[((), 'index.rst')]}
    a_rst = {(key, args) for key, args in deps.depends[((), 'a.rst')]}

    assert index_rst == {(((), 'index.rst'),None)}
    assert a_rst == {(((), 'index.rst'),None), (((), 'a.rst'),None)}

    deps.check_rebuild()
    assert not deps.rebuild

