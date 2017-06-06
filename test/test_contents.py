from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, output, main


def test_get_contents():

    site = main.Site(Path('.'))
    conts = site.contents

    a1 = contents.Article(site, '', '1', {'type': 'article'}, '1')
    a2 = contents.Article(site, 'd1', '2', {'type': 'article'}, '2')
    a3 = contents.Article(site, 'd1/d2', '3', {'type': 'article'}, '3')
    a4 = contents.Article(site, 'd3/d4', '4', {'type': 'article'}, '4')

    conts.add(a1)
    conts.add(a2)
    conts.add(a3)
    conts.add(a4)

    assert len(conts.get_contents(subdirs=[()])) == 4
    assert len(conts.get_contents(subdirs=['/d1'])) == 2
    assert len(conts.get_contents(subdirs=['/d1/d2'])) == 1
    assert len(conts.get_contents(subdirs=[('d1', 'd2')])) == 1
    assert len(conts.get_contents(subdirs=['./d2'], base=a2)) == 1
    assert len(conts.get_contents(subdirs=[('d3',)])) == 1

def test_group_items():

    site = main.Site(Path('.'))
    conts = site.contents

    a1 = contents.Article(site, '', '1', {'type': 'article', 'category':'a'}, '1')
    a2 = contents.Article(site, '', '2', {'type': 'article', 'category':'a'}, '2')
    a3 = contents.Article(site, '', '3', {'type': 'article', 'category':'b'}, '3')
    a4 = contents.Article(site, '', '4', {'type': 'snippet', 'category':'b'}, '4')

    conts.add(a1)
    conts.add(a2)
    conts.add(a3)
    conts.add(a4)

    ret = dict(conts.group_items('category', filters={'type':{'article'}}, subdirs=[()]))

    assert len(ret[('a',)]) == 2
    assert len(ret[('b',)]) == 1


def test_path_to():
    site = main.Site(Path('.'))
    conts = site.contents

    a1 = contents.Article(site, '', '1', {'type': 'article'}, '1')
    a2 = contents.Article(site, 'd1', '2', {'type': 'article'}, '2')
    a3 = contents.Article(site, 'd1/d2', '3', {'type': 'article'}, '3')

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
