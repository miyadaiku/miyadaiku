from typing import Set, List, cast
from pathlib import Path
from miyadaiku import ContentSrc, config, loader, site, context
from conftest import SiteRoot


def test_htmlcontext(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.contents / "doc.html", "hello<a>{{1+1}}</a>")
    siteroot.write_text(
        siteroot.templates / "page_article.html", "<div>{{ page.html }}</div>"
    )
    site = siteroot.load({}, {})

    ctx = context.JinjaOutput(site, ((), "doc.html"))
    (filename,), (path,) = ctx.build()
    html = Path(filename).read_text()
    assert html == "<div>hello<a>2</a></div>"
