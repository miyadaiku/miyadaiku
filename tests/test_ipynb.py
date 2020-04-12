from pathlib import Path
from miyadaiku import ipynb
from conftest import SiteRoot
from bs4 import BeautifulSoup

DIR = Path(__file__).parent


def test_load() -> None:
    metadata, text = ipynb.load(DIR / "test.ipynb")
    assert metadata["type"] == "article"
    print(text)


def test_theme(siteroot: SiteRoot) -> None:
    site = siteroot.load({"themes": ["miyadaiku.themes.ipynb"]}, {})
    template = site.jinjaenv.from_string("{{ipynb.set_header()}}")
    ret = template.render()

    soup = BeautifulSoup(ret, "html.parser")

    assert soup.head is None
    assert soup.body is None
    assert soup.title is None
    assert soup.meta is None
    assert len(soup.find_all("style")) > 1
    assert len(soup.find_all("script")) > 1
