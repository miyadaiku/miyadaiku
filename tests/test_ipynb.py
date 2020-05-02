from pathlib import Path
from miyadaiku import ipynb, ContentSrc
from conftest import SiteRoot
from bs4 import BeautifulSoup

DIR = Path(__file__).parent


def test_load() -> None:
    contentsrc = ContentSrc(
        package=None,
        srcpath=str(DIR / "test.ipynb"),
        metadata={},
        contentpath=((), "test.html"),
        mtime=0,
    )

    metadata, text = ipynb.load(contentsrc)
    assert metadata["type"] == "article"
    print(text)


def test_package() -> None:
    contentsrc = ContentSrc(
        package="pkg_ipynb",
        srcpath="files/test.ipynb",
        metadata={},
        contentpath=((), "test.html"),
        mtime=0,
    )

    metadata, text = ipynb.load(contentsrc)
    assert metadata["type"] == "article"
    print(text)


def test_theme(siteroot: SiteRoot) -> None:
    site = siteroot.load({"themes": ["miyadaiku.themes.ipynb"]}, {})
    jinjaenv = site.build_jinjaenv()
    template = jinjaenv.from_string("{{ipynb.set_header()}}")
    ret = template.render()

    soup = BeautifulSoup(ret, "html.parser")

    assert soup.head is None
    assert soup.body is None
    assert soup.title is None
    assert soup.meta is None
    assert len(soup.find_all("style")) > 1
    assert len(soup.find_all("script")) > 1


def test_theme_cssfile(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "test.html",
        """
{{ipynb.load_css(page)}}
""",
    )
    site = siteroot.load({"themes": ["miyadaiku.themes.ipynb"]}, {})
    site.build()

    s = (siteroot.outputs / "test.html").read_text()
    assert '<link href="static/ipynb/ipynb.css" rel="stylesheet"/>' in s
    assert (siteroot.outputs / "static/ipynb/ipynb.css").exists()
