from typing import Set, List, cast
from pathlib import Path
from miyadaiku import ContentSrc, config, loader, site, context


def create_site(sitedir: Path) -> site.Site:
    contentsdir = sitedir / "contents"
    filesdir = sitedir / "files"

    (contentsdir / "doc.html").write_text("hello<a>{{1+1}}</a>")

    (filesdir / "subdir").mkdir(exist_ok=True)
    (filesdir / "subdir" / "file1.txt").write_text("subdir/file1")

    (sitedir / "templates" / "page_article.html").write_text(
        "<div>{{ page.html }}</div>"
    )

    siteobj = site.Site()
    siteobj.load(sitedir, {})
    return siteobj


def test_htmlcontext(sitedir: Path) -> None:
    site = create_site(sitedir)
    ctx = context.JinjaOutput(site, ((), "doc.html"))
    (filename,), (path,) = ctx.build()
    html = Path(filename).read_text()
    assert html == "<div>hello<a>2</a></div>"


def test_binarycontext(sitedir: Path) -> None:
    site = create_site(sitedir)

    ctx = context.BinaryOutput(site, (("subdir",), "file1.txt"))
    (filename,), (path,) = ctx.build()

    assert Path(filename) == site.outputdir / "subdir/file1.txt"
    assert Path(filename).read_text() == "subdir/file1"
