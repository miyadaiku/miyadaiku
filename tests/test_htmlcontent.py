from miyadaiku import context
from conftest import SiteRoot, create_contexts


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
""",
            )
        ],
    )

    headers = ctx.content.get_headers(ctx)

    assert headers == [
        context.HTMLIDInfo(id="h_header12", tag="h1", text="header12"),
        context.HTMLIDInfo(id="h_header24", tag="h2", text="header24"),
    ]
