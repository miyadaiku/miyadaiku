from pathlib import Path
from miyadaiku.core import rst

DIR = Path(__file__).parent


def test_load():
    metadata, text = rst.load(DIR / 'test1.rst')
    assert text.strip() == '''<p>{}</p>

<div class="code-block">
<div class="code-block-caption">caption</div>
<div class="highlight"><pre><span></span>:jinja:`&#123;&#123;&#125;&#125;`
</pre></div>

</div>'''


def test_load2(tmpdir):
    f = tmpdir.join('file1.rst')
    f.write('''
..  {{ page.site_title }} --
   
''')

    metadata, text = rst.load(f)
    assert text == "<!-- &#123;&#123; page.site_title &#125;&#125; - - -->\n"


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

def test_jinjadirective(tmpdir):
    f = tmpdir.join('file1.rst')
    f.write('''
.. jinja::
   {{<a><b>}}
   <a><b>

:jinja:`{{abc}}`
''')

    metadata, text = rst.load(f)
    assert text == '''{{<a><b>}}
<a><b><p>{{abc}}</p>
'''

