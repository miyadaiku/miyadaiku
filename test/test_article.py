from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, output, main
import yaml

def test_article():
    site = main.Site(Path(''))
    article = contents.Article(site, '', 'test.rst', {}, '1234567890')
    o, = article.get_outputs()

    assert o.dirname == ()
    assert o.name == 'test.html'
    print(o.body)
    assert b'1234567890' in o.body


def test_indexpage():
    site = main.Site(Path(''))

    for i in range(10):
        site.contents.add(contents.Article(site, '', f'test{i}', {
            'type': 'article'}, f'<span>{i}</span>'))

    article = contents.IndexPage(site, '', 'test', {}, {})
    outputs = article.get_outputs()

    assert len(outputs) == 2


def test_header(sitedir):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''

.. target:: id1

title1
------------

''')

    site = main.Site(sitedir)
    site.build()
    p = site.contents.get_content('/index.rst')
    assert p.prop_get_headers(p) == [('id1', 'h1', 'title1')]


def test_header_text(sitedir):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''

---:jinja:`{{ page.link_to(page, fragment='id2') }}`---


title111
------------

.. target:: id2

title2
-----------------

''')

    site = main.Site(sitedir)
    site.build()
    p = site.contents.get_content('/index.rst')
    print(p._get_html(p))


def test_module(sitedir):
    templates = sitedir / 'templates'
    (templates / 'macro.html').write_text('''
{% macro test(s) -%}
   macro test {{ s }}
{%- endmacro %}
''')

    content = sitedir / 'contents'
    (content / 'index.rst').write_text('''

.. article::
   :imports: macro.html

:jinja:`{{ macro.test("hello") }}`
''')

    site = main.Site(sitedir)
    site.build()
    p = site.contents.get_content('/index.rst')
    print(p._get_html(p))
    assert 'macro test hello' in p._get_html(p)


def test_metadatafile(sitedir):
    content = sitedir / 'contents'
    (content / 'index.rst').write_text('')

    site = main.Site(sitedir)
    site.config.add('/', dict(generate_metadata_file=True))
    site.pre_build()

    p = site.contents.get_content('/index.rst')
    d = yaml.load((content / 'index.rst.props.yml').read_text())
    assert p.date == d['date']

    site2 = main.Site(sitedir)
    p2 = site2.contents.get_content('/index.rst')
    assert p2.date == d['date']
