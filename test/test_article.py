from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, output, main


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

    assert len(outputs) == 3
