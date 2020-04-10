from pathlib import Path
from miyadaiku import context
from conftest import SiteRoot


def test_htmlcontext(siteroot: SiteRoot) -> None:

    siteroot.write_text(siteroot.contents / "doc.html", "hello<a>{{1+1}}</a>")
    siteroot.write_text(
        siteroot.templates / "page_article.html", "<div>{{ page.html }}</div>"
    )
    site = siteroot.load({}, {})

    ctx = context.JinjaOutput(site, ((), "doc.html"))
    (filename,) = ctx.build()
    html = Path(filename).read_text()
    assert html == "<div>hello<a>2</a></div>"


def test_binarycontext(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.files / "subdir" / "file1.txt", "subdir/file1")
    site = siteroot.load({}, {})

    ctx = context.BinaryOutput(site, (("subdir",), "file1.txt"))
    (filename,) = ctx.build()

    assert Path(filename) == site.outputdir / "subdir/file1.txt"
    assert Path(filename).read_text() == "subdir/file1"


def test_load(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.contents / "A/B/C/file1.html", "A/B/C/file1.html")
    siteroot.write_text(siteroot.contents / "A/B/D/file2.html", "A/B/D/file1.html")

    site = siteroot.load({}, {})
    ctx = context.JinjaOutput(site, (("A", "B", "C"), "file1.html"))
    proxy = context.ContentProxy(ctx, ctx.content)

    file2 = proxy.load("../D/file2.html")
    assert file2.contentpath == (("A", "B", "D"), "file2.html")
