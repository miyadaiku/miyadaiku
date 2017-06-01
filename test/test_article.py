from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, output, main



def test_article():
    site = main.Site(Path(''))
    article = contents.Article(site, '', 'test.rst', {}, '1234567890')
    output,  = article.get_outputs()

    assert output.dirname == ()
    assert output.name == 'test.html'
    print(output.body)
    assert b'1234567890' in output.body


def test_indexpage():
    site = main.Site(Path(''))

    for i in range(10):
        site.contents.add(contents.Article(site, '', f'test{i}', {
                  'type': 'article'}, f'<span>{i}</span>'))

    article = contents.IndexPage(site, '', 'test', {}, {})
    outputs = article.get_outputs()

    assert len(outputs) == 3

