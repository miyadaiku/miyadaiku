from typing import cast, List
from miyadaiku import builder, context
from conftest import SiteRoot


def test_index(siteroot: SiteRoot) -> None:
    for i in range(21):
        f"tag{i % 2 + 1}"
        siteroot.write_text(
            siteroot.contents / f"htmldir/{i}.html",
            f"""
html{i}
""",
        )

    siteroot.write_text(
        siteroot.contents / "htmldir/index.yml",
        """
type: index
""",
    )

    site = siteroot.load({}, {})
    builders = builder.create_builders(
        site, site.files.get_content((("htmldir",), "index.yml"))
    )
    indexbuilders = cast(List[builder.IndexBuilder], builders)
    jinjaenv = site.build_jinjaenv()
    for b in indexbuilders:
        ctx = b.build_context(site, jinjaenv)
        (f,) = ctx.build()

    assert len(indexbuilders) == 4
    assert sum(len(b.items) for b in indexbuilders) == 21


def test_index_group(siteroot: SiteRoot) -> None:
    for i in range(21):
        tag = f"tag{i % 2 + 1}"
        siteroot.write_text(
            siteroot.contents / f"htmldir/{i}.html",
            f"""
tags: {tag}

html{i} - tag: {tag}
""",
        )

    siteroot.write_text(
        siteroot.contents / "htmldir/index.yml",
        """
type: index
groupby: tags
""",
    )

    site = siteroot.load({}, {})
    builders = builder.create_builders(
        site, site.files.get_content((("htmldir",), "index.yml"))
    )
    indexbuilders = cast(List[builder.IndexBuilder], builders)
    jinjaenv = site.build_jinjaenv()
    for b in indexbuilders:
        ctx = b.build_context(site, jinjaenv)
        assert isinstance(ctx, context.IndexOutput)

        (f,) = ctx.build()
        url = ctx.get_url()
        if ctx.cur_page == 1:
            assert f'{ctx.content.get_metadata(ctx.site, "groupby")}_{ctx.value}.html' in url
        else:
            assert (
                f'{ctx.content.get_metadata(ctx.site, "groupby")}_{ctx.value}_{ctx.cur_page}.html'
                in url
            )

    assert len(indexbuilders) == 4
    assert sum(len(b.items) for b in indexbuilders) == 21


def test_index_filter(siteroot: SiteRoot) -> None:
    for i in range(21):
        tag = f"tag{i + 1}"
        siteroot.write_text(
            siteroot.contents / f"htmldir/{i}.html",
            f"""
tags: {tag}

html{i} - tag: {tag}
""",
        )

    siteroot.write_text(
        siteroot.contents / "htmldir/index.yml",
        """
type: index
filters:
    tags: ['tag1', 'tag20']
""",
    )

    site = siteroot.load({}, {})
    (bldr,) = builder.create_builders(
        site, site.files.get_content((("htmldir",), "index.yml"))
    )
    item1, item2 = sorted(cast(builder.IndexBuilder, bldr).items)
    assert item1[1] == "0.html"
    assert item2[1] == "19.html"

    siteroot.write_text(
        siteroot.contents / "htmldir/index.yml",
        """
type: index
filters:
    tags: ['tag1', 'tag20']
excludes:
    tags: ['tag1']
""",
    )

    site = siteroot.load({}, {})
    (bldr,) = builder.create_builders(
        site, site.files.get_content((("htmldir",), "index.yml"))
    )
    (item1,) = cast(builder.IndexBuilder, bldr).items
    assert item1[1] == "19.html"


def test_index_filename(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "doc1.html",
        """
{{ page.link_to("index.yml") }}
""",
    )

    siteroot.write_text(
        siteroot.contents / "index.yml",
        """
type: index
""",
    )

    site = siteroot.load({}, {})
    site.build()

    assert (
        '<a href="index.html">index</a>' in (siteroot.outputs / "doc1.html").read_text()
    )


def test_index_group_filename(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "doc1.html",
        """
tags: tag1, tag2

{{ page.link_to("index.yml", group_value="tag1") }}
""",
    )

    for i in range(21):
        siteroot.write_text(
            siteroot.contents / f"htmldir/{i}.html",
            """
tags: tag1
""",
        )

    siteroot.write_text(
        siteroot.contents / "index.yml",
        """
type: index
groupby: tags
indexpage_max_articles: 2
""",
    )

    site = siteroot.load({}, {})
    site.build()
    assert (
        '<a href="index_tags_tag1.html">index</a>'
        in (siteroot.outputs / "doc1.html").read_text()
    )

    assert len(list(siteroot.outputs.glob("index_tags_tag1*"))) == 11
    assert len(list(siteroot.outputs.glob("index_tags_tag2*"))) == 1


def test_index_directory(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.contents / "doc1.html", "")
    siteroot.write_text(siteroot.contents / "subdir1" / "doc11.html", "")
    siteroot.write_text(siteroot.contents / "subdir1" / "subdir12" / "doc121.html", "")
    siteroot.write_text(siteroot.contents / "subdir2" / "doc21.html", "")

    siteroot.write_text(
        siteroot.contents / "index.yml",
        """
type: index
directories:
    - /
""",
    )

    site = siteroot.load({}, {})
    site.build()
    index = (siteroot.outputs / "index.html").read_text()
    assert 'href="doc1.html"' in index
    assert 'href="subdir1/doc11.html"' in index
    assert 'href="subdir1/subdir12/doc121.html"' in index
    assert 'href="subdir2/doc21.html"' in index

    siteroot.write_text(
        siteroot.contents / "index.yml",
        """
type: index
directories:
    - /subdir1
""",
    )

    site = siteroot.load({}, {})
    site.build()
    index = (siteroot.outputs / "index.html").read_text()
    assert 'href="doc1.html"' not in index
    assert 'href="subdir1/doc11.html"' in index
    assert 'href="subdir1/subdir12/doc121.html"' in index
    assert 'href="subdir2/doc21.html"' not in index

    siteroot.write_text(
        siteroot.contents / "index.yml",
        """
type: index
directories:
    - /subdir1
    - /subdir2
""",
    )

    site = siteroot.load({}, {})
    site.build()
    index = (siteroot.outputs / "index.html").read_text()
    assert 'href="doc1.html"' not in index
    assert 'href="subdir1/doc11.html"' in index
    assert 'href="subdir1/subdir12/doc121.html"' in index
    assert 'href="subdir2/doc21.html"' in index

    siteroot.write_text(
        siteroot.contents / "subdir1" / "index.yml",
        """
type: index
directories:
    - subdir12
""",
    )

    site = siteroot.load({}, {})
    site.build()
    index = (siteroot.outputs / "subdir1" / "index.html").read_text()
    assert "doc1.html" not in index
    assert "doc11.html" not in index
    assert "subdir12/doc121.html" in index
    assert "doc21" not in index
