from typing import Set, List, cast
from pathlib import Path
from miyadaiku import ContentSrc, config, loader, site, builder


def create_site(sitedir: Path):
    contentsdir = sitedir / "contents"
    filesdir = sitedir / "files"

    (sitedir / "config.yml").write_text(
        """
themes: 
    - package1
project_prop: value
"""
    )

    contentsdir.mkdir(exist_ok=True)
    (contentsdir / "root1.yml").write_text("root_prop: root_prop_value")
    (contentsdir / "root1.txt").write_text("content_root1")
    (contentsdir / "root_content1.txt").write_text("root_content1")

    rstdir = contentsdir / "rstdir"
    rstdir.mkdir(exist_ok=True)

    for i in range(21):
        (rstdir / f"{i}.rst").write_text(f"rst_{i}")

    (rstdir / "index.yml").write_text(
        """
type: index
indexpage_max_articles: 10
directory: rstdir
"""
    )

    filesdir.mkdir(exist_ok=True)
    (filesdir / "subdir").mkdir(exist_ok=True)
    (filesdir / "root1.txt").write_text("file_root1")
    (filesdir / "subdir" / "file1.txt").write_text("subdir/file1")

    siteobj = site.Site()
    siteobj.load(sitedir, {})
    return siteobj


def test_builder(sitedir: Path):
    site = create_site(sitedir)

    (b,) = builder.createBuilder(
        site, site.files.get_content((("subdir",), "file1.txt"))
    )
    ((path, contentpath),) = b.build(site)
    assert path == site.outputdir / "subdir" / "file1.txt"
    assert path.read_text() == "subdir/file1"
    assert contentpath == (("subdir",), "file1.txt")

    (b,) = builder.createBuilder(
        site, site.files.get_content(((), "package1_file1.txt"))
    )
    ((path, contentpath),) = b.build(site)
    assert path == site.outputdir / "package1_file1.txt"
    assert path.read_text() == "package1_file1.txt"
    assert contentpath == ((), "package1_file1.txt")


def test_indexbuilder(sitedir: Path):
    site = create_site(sitedir)
    pages = builder.createBuilder(
        site, site.files.get_content((("rstdir",), "index.yml"))
    )
    assert len(cast(builder.IndexBuilder, pages[0]).items) == 10
    assert len(cast(builder.IndexBuilder, pages[1]).items) == 11
