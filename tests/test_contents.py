import re

import tzlocal
from bs4 import BeautifulSoup
from conftest import SiteRoot, create_contexts

from miyadaiku import context


def test_props(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(siteroot, srcs=[("docfile.html", "hi")])

    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.abstract_length == 256
    assert proxy.article_template == "page_article.html"
    assert not proxy.category
    assert proxy.canonical_url is None
    assert proxy.charset == "utf-8"
    assert proxy.draft is False
    assert proxy.html == "hi"
    assert proxy.lang == "en-US"
    assert proxy.order == 0
    assert proxy.site_title == "(FIXME-site_title)"
    assert proxy.site_url == "http://localhost:8888/"
    assert proxy.timezone == str(tzlocal.get_localzone())
    assert proxy.title == "docfile"


def test_props_date(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(siteroot, srcs=[("doc.html", "hi")])
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.date is None

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.html",
                """
date: 2020-01-01 00:00:00+09:00
""",
            )
        ],
    )

    proxy = context.ContentProxy(ctx, ctx.content)
    assert str(proxy.date) == "2020-01-01 00:00:00+09:00"


def test_props_date_fromfilenane(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot, srcs=[("20200101.html", "hi")], config={"timezone": "UTC"}
    )
    proxy = context.ContentProxy(ctx, ctx.content)
    assert str(proxy.date) == "2020-01-01 00:00:00+00:00"

    (ctx,) = create_contexts(
        siteroot, srcs=[("2020-01-01T0203.html", "hi")], config={"timezone": "UTC"}
    )
    proxy = context.ContentProxy(ctx, ctx.content)
    assert str(proxy.date) == "2020-01-01 02:03:00+00:00"

    (ctx,) = create_contexts(
        siteroot, srcs=[("2020-::::::::.html", "hi")], config={"timezone": "UTC"}
    )
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.date is None


def test_props_updated(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(siteroot, srcs=[("doc.html", "hi")])
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.date is None

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.html",
                """
date: 2020-01-01 00:00:00+09:00
updated: 2020-01-02 00:00:00+09:00
""",
            )
        ],
    )

    proxy = context.ContentProxy(ctx, ctx.content)
    assert str(proxy.updated) == "2020-01-02 00:00:00+09:00"


def test_props_updated_default(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(siteroot, srcs=[("doc.html", "hi")])
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.date is None

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.html",
                """
date: 2020-01-01 00:00:00+09:00
""",
            )
        ],
    )

    proxy = context.ContentProxy(ctx, ctx.content)
    assert str(proxy.updated) == "2020-01-01 00:00:00+09:00"

    (ctx,) = create_contexts(siteroot, srcs=[("doc.html", "hi")])
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.date is None

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.html",
                """
""",
            )
        ],
    )

    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.updated is None


def test_filename(siteroot: SiteRoot) -> None:

    (ctx,) = create_contexts(siteroot, srcs=[("doc.md", "")])
    proxy = context.ContentProxy(ctx, ctx.content)

    assert proxy.filename == "doc.html"
    assert proxy.stem == "doc"
    assert proxy.ext == ".html"

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.md",
                """
filename: abc.def
#""",
            )
        ],
    )

    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.filename == "abc.def"

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.md",
                """
stem: 111
ext: .222
#""",
            )
        ],
    )

    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.filename == "111.222"


def test_get_abstract(siteroot: SiteRoot) -> None:
    body = "<div>123<div>456<div>789<div>abc</div>def</div>ghi</div>jkl</div>"

    maxlen = len("".join(re.sub(r"<[^>]*>", "", body).split()))

    (ctx,) = create_contexts(siteroot, srcs=[("doc.html", body)])

    def to_plain(s: str) -> str:
        return "".join(re.sub(r"<[^>]*>", "", abstract).split())

    abstract = ctx.content.build_abstract(ctx)
    txt = to_plain(abstract)
    assert len(txt) == maxlen

    for i in range(1, maxlen + 1):
        abstract = ctx.content.build_abstract(ctx, i)
        txt = to_plain(abstract)
        assert len(txt) == min(i, maxlen)


def test_get_plain_abstract(siteroot: SiteRoot) -> None:
    body = """
<div>


1   23<div>4



56<div>789<div>abc</div>def</div>ghi</div>jkl</div>
"""
    maxlen = len("".join(re.sub(r"<[^>]*>", "", body).split()))
    (ctx,) = create_contexts(siteroot, srcs=[("doc.html", body)])

    abstract = ctx.content.build_abstract(ctx, plain=True)
    assert len("".join(abstract.split())) == maxlen

    for i in range(1, maxlen + 1):
        abstract = ctx.content.build_abstract(ctx, i, plain=True)
        assert len("".join(abstract.split())) == min(i, maxlen)


def test_imports(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.html",
                """
imports: macro1.html, macro2.html

<h1>header1-{{macro1.macro1("param")}}</h1>
<h2>header2-{{macro2.macro2()}}</h2>
""",
            )
        ],
    )

    (siteroot.templates / "macro1.html").write_text(
        """
{% macro macro1(msg) -%}
   param: {{msg}}
{%- endmacro %}
"""
    )

    (siteroot.templates / "macro2.html").write_text(
        """
{% macro macro2() -%}
   macro2.macro2
{%- endmacro %}
"""
    )

    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.imports == ["macro1.html", "macro2.html"]
    assert ">header1-param: param</h1>" in proxy.html
    assert ">header2-macro2.macro2</h2>" in proxy.html


def test_parent_dirs(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(siteroot, srcs=[("a/b/c/doc.html", "")])
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.parents_dirs == [(), ("a",), ("a", "b"), ("a", "b", "c")]


def test_tags(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.html",
                """
tags: tag1, tag2
""",
            )
        ],
    )

    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.tags == ["tag1", "tag2"]


def test_url(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "doc.html",
                """
stem: aaaaa
hi""",
            )
        ],
    )

    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.url == "http://localhost:8888/aaaaa.html"

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "a/b/doc.html",
                """
filename: ../abc.html
hi""",
            )
        ],
    )

    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.url == "http://localhost:8888/a/abc.html"


def test_canonical_url(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "a/b/doc.html",
                """
canonical_url: http://example.com/aaa.html
hi""",
            )
        ],
    )
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.url == "http://example.com/aaa.html"

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "a/b/doc.html",
                """
canonical_url: ../abc.html
hi""",
            )
        ],
    )
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.url == "http://localhost:8888/a/abc.html"

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "a/b/doc.html",
                """
canonical_url: abc.html
hi""",
            )
        ],
    )
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.url == "http://localhost:8888/a/b/abc.html"


def test_strip_directory_index(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "a/b/index.html",
                """
strip_directory_index: index.html
hi""",
            )
        ],
    )
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.url == "http://localhost:8888/a/b/"

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "a/b/index2.html",
                """
strip_directory_index: index.html
hi""",
            )
        ],
    )
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.url == "http://localhost:8888/a/b/index2.html"

    (ctx,) = create_contexts(
        siteroot,
        srcs=[
            (
                "a/b/index.html",
                """
strip_directory_index: index.html
canonical_url: abc.html
hi""",
            )
        ],
    )
    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.url == "http://localhost:8888/a/b/abc.html"


def test_title(siteroot: SiteRoot) -> None:
    src1 = """
title: Title text
hi"""

    (ctx,) = create_contexts(siteroot, srcs=[("doc.html", src1)])
    assert ctx.content.build_title(ctx) == "Title text"

    src2 = """<span>01234   567890
    abcddefg</span>
    <h1>header</h1>
    """

    (ctx,) = create_contexts(
        siteroot,
        srcs=[("doc.html", src2)],
    )
    assert ctx.content.build_title(ctx) == "doc"

    (ctx,) = create_contexts(
        siteroot,
        srcs=[("doc.html", src2)],
        config={"title_fallback": "abstract", "title_abstract_len": 6},
    )
    assert ctx.content.build_title(ctx) == "01234 5"

    (ctx,) = create_contexts(
        siteroot,
        srcs=[("doc.html", src2)],
        config={"title_fallback": "header"},
    )
    assert ctx.content.build_title(ctx) == "header"


def test_headers(siteroot: SiteRoot) -> None:
    src1 = """

{% for id, tag, text in page.headers %}
    [{{id}}, {{tag}}, {{text}}]
{% endfor %}

{% for id, tag, text in page.header_anchors %}
    [{{id}}, {{tag}}, {{text}}]
{% endfor %}

<h1>text</h1>
<h1>text</h1>
"""

    (ctx,) = create_contexts(siteroot, srcs=[("doc.html", src1)])
    proxy = context.ContentProxy(ctx, ctx.content)

    html = proxy.html

    assert "[h_doc_html_text, h1, text]" in html
    assert "[h_doc_html_text_1, h1, text]" in html

    soup = BeautifulSoup(html, "html.parser")

    assert soup.select("#h_doc_html_text")[0].text == "text"
    assert soup.select("#h_doc_html_text_1")[0].text == "text"
