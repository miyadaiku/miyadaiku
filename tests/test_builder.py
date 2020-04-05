from typing import Set, List, cast
from pathlib import Path
from miyadaiku import ContentSrc, config, loader, site, builder
from conftest import SiteRoot


def test_builder(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.contents / 'subdir/file1.txt', 'subdir/file1')
    site = siteroot.load({'themes':['package1']}, {})

    (b,) = builder.createBuilder(
        site, site.files.get_content((("subdir",), "file1.txt"))
    )

    (path,), (contentpath,) = b.build(site)
    assert path == site.outputdir / "subdir" / "file1.txt"
    assert path.read_text() == "subdir/file1"
    assert contentpath == (("subdir",), "file1.txt")


    (b,) = builder.createBuilder(
        site, site.files.get_content(((), "package1_file1.txt"))
    )
    (path,), (contentpath,) = b.build(site)
    assert path == site.outputdir / "package1_file1.txt"
    assert path.read_text() == "package1_file1.txt"
    assert contentpath == ((), "package1_file1.txt")


def test_indexbuilder(siteroot: SiteRoot) -> None:
    for i in range(21):
        siteroot.write_text(siteroot.contents/  f"rstdir/{i}.rst", f"rst_{i}")



    siteroot.write_text(siteroot.contents / "rstdir/index.yml",
        """
type: index
indexpage_max_articles: 10
directory: rstdir
"""
    )

    site = siteroot.load({}, {})


    pages = builder.createBuilder(
        site, site.files.get_content((("rstdir",), "index.yml"))
    )
    assert len(cast(builder.IndexBuilder, pages[0]).items) == 10
    assert len(cast(builder.IndexBuilder, pages[1]).items) == 11
