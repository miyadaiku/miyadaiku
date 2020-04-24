import re
from miyadaiku import context
from conftest import SiteRoot, create_contexts
import tzlocal


def test_props(siteroot: SiteRoot) -> None:
    (ctx,) = create_contexts(siteroot, srcs=[("docfile.html", "hi")])

    proxy = context.ContentProxy(ctx, ctx.content)
    assert proxy.abstract_length == 500
    assert proxy.article_template == "page_article.html"
    assert proxy.category == ""
    assert proxy.canonical_url is None
    assert proxy.charset == "utf-8"
    assert proxy.draft is False
    assert proxy.html == "hi"
    assert proxy.lang == "en-US"
    assert proxy.order == 0
    assert proxy.site_title == "(FIXME-site_title)"
    assert proxy.site_url == "http://localhost:8888/"
    assert proxy.timezone == tzlocal.get_localzone().zone
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
    body = f"<div>123<div>456<div>789<div>abc</div>def</div>ghi</div>jkl</div>"

    (ctx,) = create_contexts(siteroot, srcs=[("doc.html", body)])

    abstract = ctx.content.build_abstract(ctx, 2)
    txt = re.sub(r"<[^>]*>", "", abstract)
    assert len(txt) == 2

    abstract = ctx.content.build_abstract(ctx, 6)
    txt = re.sub(r"<[^>]*>", "", abstract)
    assert len(txt) == 6

    abstract = ctx.content.build_abstract(ctx, 14)
    txt = re.sub(r"<[^>]*>", "", abstract)
    assert len(txt) == 14

    abstract = ctx.content.build_abstract(ctx, 100)
    txt = re.sub(r"<[^>]*>", "", abstract)
    assert len(txt) == 21

    proxy = context.ContentProxy(ctx, ctx.content)
    txt = re.sub(r"<[^>]*>", "", str(proxy.abstract))
    assert len(txt) == 21


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
    assert "<h1>header1-param: param</h1>" in proxy.html
    assert "<h2>header2-macro2.macro2</h2>" in proxy.html


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
