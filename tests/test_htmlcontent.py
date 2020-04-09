from miyadaiku import context
from conftest import SiteRoot, create_contexts
from bs4 import BeautifulSoup


def test_get_headers(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.html",
                """
<h1>header1{{1+1}}</h1>
<div>body1</div>

<h2>header2{{2+2}}</h2>
<div>body2</div>

<div class="header_target" id="abcdefg"></div>
<h2>header3{{3+3}}</h2>
<div>body3</div>

""",
            )
        ],
    )

    headers = ctx.content.get_headers(ctx)

    assert headers == [
        context.HTMLIDInfo(id="h_header12", tag="h1", text="header12"),
        context.HTMLIDInfo(id="h_header24", tag="h2", text="header24"),
        context.HTMLIDInfo(id="h_header36", tag="h2", text="header36"),
    ]
    print(ctx.content.build_html(ctx))


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


def test_header_target(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.html",
                """
<div class="header_target" id="xyz">
    <h1>header_xyz{{1+1}}</h1>
</div>
<div>body1</div>
""",
            )
        ],
    )
    proxy = context.ContentProxy(ctx, ctx.content)
    link = proxy.link(fragment="xyz")
    soup = BeautifulSoup(link, "html.parser")
    assert soup.a.text == "header_xyz2"
    assert soup.a["href"] == "doc.html#xyz"


def test_link_xref(siteroot: SiteRoot) -> None:
    (ctx1, ctx2) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc1.html",
                """
<h1>doc1-header1</h1>
{{page.link_to("doc2.html", fragment="h_doc2header1")}}
""",
            ),
            (
                "doc2.html",
                """<h1>doc2-header1</h1>
{{page.link_to("doc1.html", fragment="h_doc1header1")}}

""",
            ),
        ],
    )
    proxy1 = context.ContentProxy(ctx1, ctx1.content)
    soup = BeautifulSoup(proxy1.html, "html.parser")
    a = soup.find_all("a")[-1]
    assert a["href"] == "doc2.html#h_doc2header1"
    assert a.text == "doc2-header1"

    proxy2 = proxy1.load("doc2.html")
    soup = BeautifulSoup(proxy2.html, "html.parser")
    a = soup.find_all("a")[-1]
    assert a["href"] == "doc1.html#h_doc1header1"
    assert a.text == "doc1-header1"


def test_link_recurse(siteroot: SiteRoot) -> None:
    (ctx1, ctx2) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc1.html",
                """
<div class="header_target" id="doc1_id1">
<h1>doc1-header1
{{content.link_to("doc2.html", fragment="doc2_id1")}}
</h1>
</div>
""",
            ),
            (
                "doc2.html",
                """
<div class="header_target" id="doc2_id1">
<h1>doc2-header1
{{content.link_to("doc1.html", fragment="doc1_id1")}}
</h1>
</div>
""",
            ),
        ],
    )
    proxy1 = context.ContentProxy(ctx1, ctx1.content)
    soup = BeautifulSoup(proxy1.html, "html.parser")
    a = soup.find_all("a")[-1]
    assert "Circular reference detected" in a.text

    proxy2 = context.ContentProxy(ctx1, ctx2.content)
    soup = BeautifulSoup(proxy2.html, "html.parser")
    a = soup.find_all("a")[-1]
    assert "Circular reference detected" in a.text
