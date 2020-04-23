from typing import cast, List, Any
from unittest.mock import patch
from miyadaiku import builder
from conftest import SiteRoot


def test_builder(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.contents / "subdir/file1.txt", "subdir/file1")
    site = siteroot.load({"themes": ["package1"]}, {})

    (b,) = builder.create_builders(
        site, site.files.get_content((("subdir",), "file1.txt"))
    )

    jinjaenv = site.build_jinjaenv()
    context = b.build_context(site, jinjaenv)
    (path,) = context.build()
    assert path == site.outputdir / "subdir" / "file1.txt"
    assert path.read_text() == "subdir/file1"

    (b,) = builder.create_builders(
        site, site.files.get_content(((), "package1_file1.txt"))
    )

    jinjaenv = site.build_jinjaenv()
    context = b.build_context(site, jinjaenv)
    (path,) = context.build()
    assert path == site.outputdir / "package1_file1.txt"
    assert path.read_text() == "package1_file1.txt"


def test_indexbuilder(siteroot: SiteRoot) -> None:
    for i in range(21):
        siteroot.write_text(siteroot.contents / f"rstdir/{i}.rst", f"rst_{i}")

    siteroot.write_text(
        siteroot.contents / "rstdir/index.yml",
        """
type: index
indexpage_max_articles: 10
directory: rstdir
""",
    )

    site = siteroot.load({}, {})

    builders = builder.create_builders(
        site, site.files.get_content((("rstdir",), "index.yml"))
    )

    indexbuilders = cast(List[builder.IndexBuilder], builders)

    assert indexbuilders[0].cur_page == 1
    assert indexbuilders[0].num_pages == 2
    assert len(indexbuilders[0].items) == 10

    assert indexbuilders[1].cur_page == 2
    assert indexbuilders[1].num_pages == 2
    assert len(indexbuilders[1].items) == 11


def test_indexbuilder_group(siteroot: SiteRoot) -> None:
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

    assert len(indexbuilders) == 4

    assert indexbuilders[0].cur_page == 1
    assert indexbuilders[0].num_pages == 2
    assert indexbuilders[0].value == "tag1"
    assert len(indexbuilders[0].items) == 5

    assert indexbuilders[1].cur_page == 2
    assert indexbuilders[1].num_pages == 2
    assert indexbuilders[1].value == "tag1"
    assert len(indexbuilders[1].items) == 6

    assert indexbuilders[2].cur_page == 1
    assert indexbuilders[2].num_pages == 2
    assert indexbuilders[2].value == "tag2"
    assert len(indexbuilders[2].items) == 5

    assert indexbuilders[3].cur_page == 2
    assert indexbuilders[3].num_pages == 2
    assert indexbuilders[3].value == "tag2"
    assert len(indexbuilders[3].items) == 5

    jinjaenv = site.build_jinjaenv()
    context = indexbuilders[0].build_context(site, jinjaenv)
    assert context.contentpath == (("htmldir",), "index.yml")


@patch("multiprocessing.cpu_count", return_value=3)
def test_split_batch(cpu_count: Any) -> None:

    ret = builder.split_batch([i for i in range(25)])
    assert len(ret) == 2
    assert set(ret[0] + ret[1]) == set(range(25))

    with patch("miyadaiku.builder.MIN_BATCH_SIZE", 1):

        ret = builder.split_batch([1])
        assert ret == [[1]]

        ret = builder.split_batch([i for i in range(3)])
        assert ret == [[0], [1], [2]]

        ret = builder.split_batch([i for i in range(4)])
        assert ret == [[0, 3], [1], [2]]

        ret = builder.split_batch([i for i in range(6)])
        assert ret == [[0, 3], [1, 4], [2, 5]]


def test_mpbuild(siteroot: SiteRoot) -> None:

    siteroot.write_text(siteroot.contents / "test.txt", "test")
    site = siteroot.load({}, {})

    site.build()
