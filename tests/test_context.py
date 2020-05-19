from pathlib import Path
from miyadaiku import context, exceptions
from conftest import SiteRoot, create_contexts
from bs4 import BeautifulSoup
import pytest


def test_htmlcontext(siteroot: SiteRoot) -> None:

    siteroot.write_text(siteroot.contents / "doc.html", "hello<a>{{1+1}}</a>")
    siteroot.write_text(
        siteroot.templates / "page_article.html", "<div>{{ page.html }}</div>"
    )
    site = siteroot.load({}, {})
    jinjaenv = site.build_jinjaenv()

    ctx = context.JinjaOutput(site, jinjaenv, ((), "doc.html"))
    (filename,) = ctx.build()
    html = Path(filename).read_text()
    assert html == "<div>hello<a>2</a></div>"


def test_binarycontext(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.files / "subdir" / "file1.txt", "subdir/file1")
    site = siteroot.load({}, {})

    jinjaenv = site.build_jinjaenv()
    ctx = context.BinaryOutput(site, jinjaenv, (("subdir",), "file1.txt"))
    (filename,) = ctx.build()

    assert Path(filename) == site.outputdir / "subdir/file1.txt"
    assert Path(filename).read_text() == "subdir/file1"


def test_load(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.contents / "A/B/C/file1.html", "A/B/C/file1.html")
    siteroot.write_text(siteroot.contents / "A/B/D/file2.html", "A/B/D/file1.html")

    site = siteroot.load({}, {})
    jinjaenv = site.build_jinjaenv()
    ctx = context.JinjaOutput(site, jinjaenv, (("A", "B", "C"), "file1.html"))
    proxy = context.ContentProxy(ctx, ctx.content)

    file2 = proxy.load("../D/file2.html")
    assert file2.contentpath == (("A", "B", "D"), "file2.html")


def test_path_to(siteroot: SiteRoot) -> None:
    ctx1, ctx2, ctx3 = create_contexts(
        siteroot,
        srcs=[
            ("a/b/c/doc1.html", ""),
            ("a/b/c/doc2.html", ""),
            ("a/b/d/doc3.html", ""),
        ],
    )

    proxy = context.ContentProxy(ctx1, ctx1.content)
    path = proxy.path_to("/a/b/c/doc2.html")
    assert path == "doc2.html"

    path = proxy.path_to("/a/b/d/doc3.html")
    assert path == "../d/doc3.html"

    path = proxy.path_to("../d/doc3.html", fragment="fragment1")
    assert path == "../d/doc3.html#fragment1"

    path = proxy.path_to("../d/doc3.html", abs_path=True)
    assert path == "http://localhost:8888/a/b/d/doc3.html"

    ctx1.content.use_abs_path = True
    path = proxy.path_to("../d/doc3.html")
    assert path == "http://localhost:8888/a/b/d/doc3.html"


def test_link(siteroot: SiteRoot) -> None:
    (ctx1, ctx2) = create_contexts(
        siteroot,
        srcs=[
            ("doc1.html", "",),
            (
                "doc2.html",
                """
<h1>he<span>a</span>der1</h1>
<div>body1</div>

<h2>header2</h2>
<div>body2</div>
""",
            ),
        ],
    )

    proxy1 = context.ContentProxy(ctx1, ctx1.content)
    proxy2 = context.ContentProxy(ctx1, ctx2.content)

    link = proxy1.link_to("doc2.html")
    soup = BeautifulSoup(link, "html.parser")
    assert soup.a["href"] == "doc2.html"
    assert str(soup.a.text) == "doc2"

    link = proxy2.link()
    soup = BeautifulSoup(link, "html.parser")
    assert soup.a["href"] == "doc2.html"
    assert soup.a.text == "doc2"

    link = proxy2.link(text="<>text<>")
    soup = BeautifulSoup(link, "html.parser")
    assert soup.a.text == "<>text<>"

    link = proxy2.link(fragment="h_header1")
    soup = BeautifulSoup(link, "html.parser")
    assert soup.a["href"] == "doc2.html#h_header1"
    assert soup.a.text == "header1"

    link = proxy2.link(fragment="h_header1", text="text")
    soup = BeautifulSoup(link, "html.parser")
    assert soup.a.text == "text"

    link = proxy2.link(fragment="h_header1")
    soup = BeautifulSoup(link, "html.parser")
    assert soup.a["href"] == "doc2.html#h_header1"
    assert soup.a.text == "header1"

    link = proxy2.link(abs_path=True)
    soup = BeautifulSoup(link, "html.parser")
    assert soup.a["href"] == "http://localhost:8888/doc2.html"

    link = proxy2.link(fragment="h_header2")
    soup = BeautifulSoup(link, "html.parser")
    assert soup.a.text == "header2"

    link = proxy2.link(attrs={"class": "classname", "style": "border:solid"})
    soup = BeautifulSoup(link, "html.parser")
    assert soup.a.text == "doc2"
    soup.a["class"] == "classname"
    soup.a["style"] == "border:solid"


def test_contentsproxy(siteroot: SiteRoot) -> None:
    (ctx1, ctx2) = create_contexts(
        siteroot,
        srcs=[
            (
                "a/b/c/doc1.html",
                """
tags: tag1
""",
            ),
            (
                "a/b/doc2.html",
                """
tags: tag2
""",
            ),
        ],
    )

    proxy = context.ContentsProxy(ctx1, ctx1.content)
    assert ctx2.content is proxy.get_content("/a/b/doc2.html").content
    assert ctx2.content is proxy.get_content("../doc2.html").content
    assert ctx2.content is proxy["../doc2.html"].content

    assert [ctx1.content] == [
        c.content for c in proxy.get_contents(filters={"tags": "tag1"})
    ]
    assert [ctx1.content] == [c.content for c in proxy.get_contents(subdirs=["/a/b/c"])]
    assert {ctx1.content, ctx2.content} == {
        c.content for c in proxy.get_contents(subdirs=["/a/b"])
    }
    assert {ctx2.content} == {
        c.content for c in proxy.get_contents(subdirs=["/a/b"], recurse=False)
    }

    (tags1, files1), (tags2, files2) = sorted(proxy.group_items(group="tags"))
    assert tags1 == ("tag1",)
    assert [ctx1.content] == [c.content for c in files1]
    assert tags2 == ("tag2",)
    assert [ctx2.content] == [c.content for c in files2]


def test_configproxy(siteroot: SiteRoot) -> None:
    (ctx1, ctx2) = create_contexts(
        siteroot,
        srcs=[
            (
                "a/b/c/doc1.html",
                """
""",
            ),
            (
                "a/b/c/doc2.yaml",
                """
type: config
prop1: value1
""",
            ),
            (
                "a/b/doc3.html",
                """
""",
            ),
            (
                "a/b/doc4.yaml",
                """
type: config
prop1: value2
prop2: value3
""",
            ),
        ],
    )

    proxy = context.ConfigProxy(ctx1, ctx1.content)
    assert "value1" == proxy["prop1"]
    assert "value3" == proxy["prop2"]
    assert "value1" == proxy.get(None, "prop1")
    assert "value1" == proxy.get(".", "prop1")
    assert "value2" == proxy.get("..", "prop1")

    with pytest.raises(exceptions.ConfigNotFound):
        assert proxy["prop3"]
