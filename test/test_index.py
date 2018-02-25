import re
import pytest
import pathlib
from miyadaiku.core import main


def _create_content(sitedir):
    sitedir.joinpath('config.yml').write_text('')

    content = sitedir / 'contents'

    for i in range(20):
        src = '''
.. article::
   :date: 2017-01-01
   :category: cat: 1

%d.rst
----------------

article body
''' % i

        content.joinpath('%i.rst' % i).write_text(src)


def test_index(sitedir):
    _create_content(sitedir)

    content = sitedir / 'contents'
    content.joinpath('index.yml').write_text("""
type: index
indexpage_max_articles: 4
""")

    site = main.Site(sitedir)
    site.build()

    nums = [re.search(r'\d', p.stem + '_1')[0] for p in sitedir.joinpath('outputs').glob('index*')]
    assert set(int(d) for d in nums) == set([1, 2, 3, 4, 5])
    for p in sitedir.joinpath('outputs').glob('index*'):
        print(p.read_text())

    index = site.contents.get_content('/index.yml')
    assert index.path_to(index, npage=2) == 'index_2.html'


def test_group(sitedir):
    _create_content(sitedir)

    content = sitedir / 'contents'
    content.joinpath('index.yml').write_text("""
type: index
indexpage_max_articles: 4
groupby: category
""")

    site = main.Site(sitedir)
    site.build()

    files = [p.stem for p in sitedir.joinpath('outputs').glob('index*')]
    assert len(files) == 5
    assert 'index_category_cat@3a@201' in files

    nums = (re.search(r'_(\d)$', p) for p in files)
    assert set(int(m[1]) for m in nums if m) == set([2, 3, 4, 5])

    for p in sitedir.joinpath('outputs').glob('index*'):
        print(p.read_text())
