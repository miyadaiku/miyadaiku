import re
import pytest
import pathlib
from miyadaiku.core import main
from testutil import sitedir

def test_index(sitedir):
    sitedir.joinpath('config.yml').write_text('')

    content = sitedir / 'contents'
    
    for i in range(20):
        src = '''
.. article::
   :date: 2017-01-01

%d.rst
----------------

article body
''' % i

        content.joinpath('%i.rst' % i).write_text(src)

    content.joinpath('index.yml').write_text("""
type: index
indexpage_max_articles: 4
""")

    site = main.Site(sitedir)
    site.build()
    site.write()

    nums = [re.search(r'\d', p.stem+'_1')[0] for p in sitedir.joinpath('outputs').glob('index*')]
    assert set(int(d) for d in nums) == set([1,2,3,4,5])
    for p in sitedir.joinpath('outputs').glob('index*'):
        print(p.read_text())
    