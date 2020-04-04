from typing import Set, List, cast
from pathlib import Path
from miyadaiku import ContentSrc, config, loader, site, context


def create_site(sitedir: Path):
    contentsdir = sitedir / "contents"
    filesdir = sitedir / "files"

    (contentsdir / "doc.html").write_text("hello<a></a>")

    (filesdir / "subdir").mkdir(exist_ok=True)
    (filesdir / "subdir" / "file1.txt").write_text("subdir/file1")

    (sitedir/ "templates" / "page_article.html").write_text("{{ page.html }}")

    siteobj = site.Site()
    siteobj.load(sitedir, {})
    return siteobj


def test_htmlcontext(sitedir:Path):
    site = create_site(sitedir)
    ctx = context.HTMLOutput(site, ((), "doc.html"))
    (filename,), (path,) = ctx.build()
    html = Path(filename).read_text()
    assert html == 'hello<a></a>'


def test_binarycontext(sitedir: Path):
    site = create_site(sitedir)

    ctx = context.BinaryOutput(site, (("subdir",), "file1.txt"))
    (filename,), (path,) = ctx.build()

    assert Path(filename) == site.outputdir / "subdir/file1.txt"
    assert Path(filename).read_text() == "subdir/file1"

