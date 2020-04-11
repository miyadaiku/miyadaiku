from miyadaiku import context
from conftest import SiteRoot, create_contexts
from bs4 import BeautifulSoup


def test_build(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(siteroot, srcs=[("doc.html", "{{page.title}}",)],)

    (path,) = ctx.build()
    assert path == ctx.site.outputdir / "doc.html"


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
