from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, output, main


def test_path_to():
    site = main.Site(Path('.'))
    conts = site.contents

    a1 = contents.Article(site.config, '', '1', {'type': 'article'}, '1')
    a2 = contents.Article(site.config, 'd1', '2', {'type': 'article'}, '2')
    a3 = contents.Article(site.config, 'd1/d2', '3', {'type': 'article'}, '3')

    conts.add(a1)
    conts.add(a2)
    conts.add(a3)

    assert conts.get_content('1', a1).name == '1'
    assert conts.get_content('d1/2', a1).name == '2'
    assert conts.get_content('./d1/2', a1).name == '2'
    assert conts.get_content('/d1/../1', a1).name == '1'
    assert conts.get_content('3', a3).name == '3'
    assert conts.get_content('../2', a3).name == '2'


def test_get_abstract():
    site = main.Site(Path('.'))
    conts = site.contents

    s = '0123456789' * 5
    body = f'<div>{s}<div>{s}<div>{s}<div>{s}</div><p>{s}</p></div></div></div>'*10

    a = contents.Article(site, '', '1', {'type': 'article'}, body)

    ss= a.prop_get_abstract(a)


def test_categories():
    site = main.Site(Path('.'))

    a1 = contents.Article(site, '', '1', 
        {'type': 'article', 'category': 'A', 'tags': ['1', '2']}, '1')
    a2 = contents.Article(site, 'd1', '2', {'type': 'article', 'category': 'A', 'tags': ['2', '3']}, '2')
    a3 = contents.Article(site, 'd1/d2', '3',{'type': 'article', 'category': 'B'}, '3')

    site.contents.add(a1)
    site.contents.add(a2)
    site.contents.add(a3)

    assert site.contents.categories == ['A', 'B']
    assert site.contents.tags == ['1', '2', '3']
