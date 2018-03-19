from pathlib import Path
from miyadaiku.core import rst, contents, config, main

DIR = Path(__file__).parent
SITE = DIR / 'site1'


def test_load():
    fname = SITE / 'contents/test.rst'
    metadata, body = rst.load(fname)
    assert metadata == {
        "title": "title",
        "filename": "slug name",
        "type": "article",
    }


def test_fileloader():
    site = main.Site(Path(''))
    contents.load_directory(site, SITE / 'contents')
    all = list(site.contents.get_contents(filters={
        'type': {'binary', 'article', 'index', 'config'}
        }))
    assert len(all) == 4

    rst = site.contents.get_content('/test.rst')
    assert rst.abcdefg == 'hijklmn'


def test_packageloader():
    site = main.Site(Path(''))
    contents.load_package(site, 'package1', 'contents',)
    all = list(site.contents.get_contents(filters={
        'type': {'binary', 'article', 'index', 'config'}
        }))

    assert len(all) == 7
    assert site.contents.get_content(
        '/dir1/test.rst').body.strip() == '<p>package1/dir1/test.rst</p>'

    rst = site.contents.get_content('/dir1/test.rst')
    assert rst.abcdefg == 'hijklmn'
