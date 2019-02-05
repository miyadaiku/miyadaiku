from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv
from miyadaiku.core.site import Site
import yaml
from bs4 import BeautifulSoup


def test_article(sitedir):
    site = Site(sitedir)
    article = contents.Article(site, '', 'test.rst', {}, '1234567890')
    files, context = article.build(sitedir / 'outputs')

    assert article.dirname == ()
    assert article.filename == 'test.html'
    assert b'1234567890' in Path(files[0]).read_bytes()


def test_title(sitedir):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''

:jinja:`{{xx}}<a>` abc<>
------------------------------------------------

body
''')

    site = Site(sitedir)
    site.build()
    p = site.contents.get_content('/index.rst')
    assert p.title == '{{xx}} abc<>'
    html = BeautifulSoup((sitedir / 'outputs/index.html').read_text())
    assert html.h1.decode_contents().strip() == '{{xx}} abc&lt;&gt;'


def test_indexpage(sitedir):
    site = Site(sitedir)

    for i in range(10):
        site.contents.add(contents.Article(site, '', f'test{i}', {
            'type': 'article'}, f'<span>{i}</span>'))

    article = contents.IndexPage(site, '', 'test', {}, '')
    files, context = article.build(sitedir / 'outputs')

    assert len(files) == 2


def test_header(sitedir):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''

.. target:: id1

title1<>
------------

title1<>
------------

xxxx

title2<>
==========

title3 http://example.com
==============================



''')

    site = Site(sitedir)
    site.build()
    p = site.contents.get_content('/index.rst')
    context = contents._context(site, p)

    print(p.prop_get_headers(context))
    assert p.prop_get_headers(context) == [
        ('h_title1', 'h1', 'title1<>'),
        ('h_title1_1', 'h1', 'title1<>'),
        ('h_title2', 'h2', 'title2<>'),
        ('h_title3httpexample.com', 'h2', 'title3 http://example.com')]

    assert p.prop_get_fragments(context) == [('id1', 'h1', 'title1<>')]

    html = p._get_html(context)
    soup = BeautifulSoup(html, 'html.parser')
    print(html)


def test_header_text(sitedir):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''

TITLE<>
=========================

+++ :jinja:`{{ page.link_to(page) }}` +++


--- :jinja:`{{ page.link_to(page, fragment='h_title2') }}` ---


title111
------------

abc

title2<>
-----------------

''')

    site = Site(sitedir)
    p = site.contents.get_content('/index.rst')
    context = contents._context(site, p)
    ret = p._get_html(context)
    print(ret)
    assert '+++ <a href="index.html">TITLE&lt;&gt;</a> +++' in ret
    assert '--- <a href="index.html#h_title2">title2&lt;&gt;</a> ---' in ret

def test_unicode_header(sitedir):

    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''

.. jinja::

   {% for id, elem, text in page.headers %}
     <div>
       {{ page.link_to(page, fragment=id) }}
     </div>
   {% endfor %}


あ
------------

abc

か
-----------------

def

''')

    site = Site(sitedir)
    p = site.contents.get_content('/index.rst')
    context = contents._context(site, p)
    ret = p._get_html(context)
    print(ret)

    assert '<a href="index.html#h_%E3%81%82">あ</a>' in ret
    assert '<a href="index.html#h_%E3%81%8B">か</a>' in ret

    assert ('<div class="md_header_block" id="h_%E3%81%82">'
            '<a class="md_header_anchor" id="a_%E3%81%82"></a><h1>あ</h1></div>') in ret
    assert ('<div class="md_header_block" id="h_%E3%81%8B">'
            '<a class="md_header_anchor" id="a_%E3%81%8B"></a><h1>か</h1></div>') in ret


def test_fragment_text(sitedir):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''

---:jinja:`{{ page.link_to(page, fragment='id2') }}`---


title111
------------

.. target:: id2

title2<>
-----------------

''')

    site = Site(sitedir)
    site.build()
    p = site.contents.get_content('/index.rst')
    context = contents._context(site, p)
    ret = p._get_html(context)
    print(ret)
    assert '---<a href="index.html#id2">title2&lt;&gt;</a>---' in ret


def test_link_to(sitedir):
    content = sitedir / 'contents'
    content.joinpath('file1.rst').write_text('''
---:jinja:`{{ page.link_to(page, fragment='id2') }}`---


.. target:: id2

title111<> :jinja:`<abc/>`
--------------------------------

asdfasdf
''')

    site = Site(sitedir)
    site.build()
    p = site.contents.get_content('/file1.rst')
    context = contents._context(site, p)
    ret = p._get_html(context)
    print(ret)

    assert 'title111&lt;&gt;</a>---' in ret


def test_link_to2(sitedir):
    content = sitedir / 'contents'
    content.joinpath('file1.rst').write_text('''
title111<>
--------------------------------

asdfasdf
''')

    content.joinpath('file2.rst').write_text('''

:jinja:`{{ page.link_to('./file1.rst') }}`

''')

    site = Site(sitedir)
    site.build()
    p = site.contents.get_content('/file2.rst')
    context = contents._context(site, p)
    ret = p._get_html(context)
    assert 'title111&lt;&gt;</a>' in ret



def test_fragment_error(sitedir):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''

---:jinja:`{{ page.link(fragment='xxxxx') }}`---



title2<>
-----------------

''')

    site = Site(sitedir)
    p = site.contents.get_content('/index.rst')
    context = contents._context(site, p)
    try:
        ret = p._get_html(context)
    except Exception as e:
        assert str(e).startswith('Cannot find fragment: xxxxx')


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

    site = Site(sitedir)
    site.build()
    p = site.contents.get_content('/index.rst')
    context = contents._context(site, p)
    print(p._get_html(context))
    assert 'macro test hello' in p._get_html(context)


def test_metadatafile(sitedir):
    content = sitedir / 'contents'
    (content / 'index.rst').write_text('')

    site = Site(sitedir)
    site.config.add('/', dict(generate_metadata_file=True))
    site.pre_build()

    p = site.contents.get_content('/index.rst')
    d = yaml.load((content / 'index.rst.props.yml').read_text())
    assert p.date == d['date']

    site2 = Site(sitedir)
    p2 = site2.contents.get_content('/index.rst')
    assert p2.date == d['date']
