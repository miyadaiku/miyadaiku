from pathlib import Path
from miyadaiku.core import rst

DIR = Path(__file__).parent


def test_load():
    metadata, text = rst.load(DIR / 'test1.rst')
    assert text.strip() == '''<p>{}</p>
<div class="highlight"><pre><span></span>:jinja:`&#123;&#123;&#125;&#125;`
</pre></div>'''


def test_date(tmpdir):
    f = tmpdir.join('file1.rst')
    f.write('''
.. article::
   :date: 2017-01-01
   :filename: slug name
   :aaa: 100
''')

    metadata, text = rst.load(f)
    print(metadata, text)

