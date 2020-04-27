from typing import Set
from miyadaiku import ContentSrc, config, loader, site, contents
from conftest import SiteRoot


def test_walk_directory(siteroot: SiteRoot) -> None:

    file1 = siteroot.write_text(siteroot.contents / "dir1/file1", "")
    siteroot.write_text(siteroot.contents / "dir1/file1.props.yml", "name: value")
    file2 = siteroot.write_text(siteroot.contents / "dir1/dir2/file2", "")
    siteroot.write_text(siteroot.contents / "dir1/file3.bak", "")

    results = loader.walk_directory(siteroot.contents, set(["*.bak"]))

    all = sorted(results, key=lambda d: d.srcpath)
    assert len(all) == 2

    assert all[0] == ContentSrc(
        srcpath=str(file2),
        contentpath=(("dir1", "dir2",), "file2"),
        package="",
        metadata={},
        mtime=all[0].mtime,
    )
    assert all[1] == ContentSrc(
        srcpath=str(file1),
        contentpath=(("dir1",), "file1"),
        package="",
        metadata={"name": "value"},
        mtime=all[1].mtime,
    )


def test_walkpackage() -> None:
    results = loader.walk_package("package1", "contents", set(["*.bak"]))
    all = sorted(results, key=lambda d: d.srcpath)

    assert len(all) == 7
    assert all[0] == ContentSrc(
        package="package1",
        srcpath="contents/dir1/a",
        contentpath=(("dir1",), "a"),
        metadata={"test": "value"},
        mtime=all[0].mtime,
    )


def test_loadfiles(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.contents / "root1.yml", "root_prop: root_prop_value")
    siteroot.write_text(siteroot.contents / "root1.txt", "content_root1")
    siteroot.write_text(siteroot.contents / "root_content1.txt", "root_content1")

    siteroot.write_text(siteroot.files / "root1.txt", "file_root1")
    siteroot.write_text(siteroot.files / "root_file1.txt", "root_file1")
    siteroot.write_text(siteroot.files / "root_file2.rst", "root_file2")

    files = loader.ContentFiles()
    cfg = config.Config({})
    root = siteroot.path
    ignores: Set[str] = set()
    themes = ["package3", "package4"]

    site = siteroot.load({}, {})
    loader.loadfiles(site, files, cfg, root, ignores, themes)

    assert len(files._contentfiles) == 8
    assert files._contentfiles[((), "root1.txt")].get_body() == b"content_root1"
    assert files._contentfiles[((), "root_content1.txt")].get_body() == b"root_content1"
    assert files._contentfiles[((), "root_file1.txt")].get_body() == b"root_file1"
    assert isinstance(files._contentfiles[((), "root_file2.rst")], contents.BinContent)

    assert (
        files._contentfiles[((), "package3_root.rst")].get_body().strip()
        == b"<p>package3/contents/package3_root.rst</p>"
    )
    assert (
        files._contentfiles[((), "package_root.rst")].get_body().strip()
        == b"<p>package3/contents/package_root.rst</p>"
    )
    package3_files_1 = files._contentfiles[((), "package3_files_1.rst")]
    assert isinstance(package3_files_1, contents.BinContent)
    assert package3_files_1.get_body().strip() == b"package3/files/package3_file_1.rst"

    assert (
        files._contentfiles[((), "package4_root.rst")].get_body().strip()
        == b"<p>package4/contents/package4_root.rst</p>"
    )

    assert cfg.get((), "root_prop") == "root_prop_value"
    assert cfg.get((), "package3_prop_a1") == "value_package3_a1"


def test_get_contents(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "a.rst",
        """
.. article::
   :date: 2017-01-01
   :category: A
   :tags: tag1, tag2
   :prop1: propvalue1
test
""",
    )

    siteroot.write_text(
        siteroot.contents / "b.rst",
        """
.. article::
   :date: 2017-01-02
   :category: B
   :tags: tag1, tag3

test
""",
    )

    siteroot.write_text(
        siteroot.contents / "sub1/c.rst",
        """
.. article::
   :date: 2017-01-03
   :category: C
   :tags: tag2, tag3

test
""",
    )

    s = site.Site()
    s = siteroot.load({}, {})

    found = s.files.get_contents(s)
    assert set(f.src.contentpath for f in found) == set(
        [((), "a.rst"), ((), "b.rst"), (("sub1",), "c.rst")]
    )

    found = s.files.get_contents(s, filters=dict(prop1="propvalue1"))
    assert set(f.src.contentpath for f in found) == set([((), "a.rst")])

    found = s.files.get_contents(s, filters=dict(tags=("tag1")))
    assert set(f.src.contentpath for f in found) == set([((), "a.rst"), ((), "b.rst")])

    found = s.files.get_contents(s, filters=dict(tags=("tag1", "tag2")))
    assert set(f.src.contentpath for f in found) == set(
        [((), "a.rst"), ((), "b.rst"), (("sub1",), "c.rst")]
    )

    groups = s.files.group_items(s, group="category", filters=dict(tags=("tag1",)))
    d = dict(groups)
    assert len(d) == 2
    assert set(f.src.contentpath for f in d[("A",)]) == set([((), "a.rst")])
    assert set(f.src.contentpath for f in d[("B",)]) == set([((), "b.rst")])

    groups = s.files.group_items(s, group="tags")
    d = dict(groups)
    assert len(d) == 3
    assert set(f.src.contentpath for f in d[("tag1",)]) == set(
        [((), "a.rst"), ((), "b.rst")]
    )
    assert set(f.src.contentpath for f in d[("tag2",)]) == set(
        [((), "a.rst"), (("sub1",), "c.rst")]
    )
    assert set(f.src.contentpath for f in d[("tag3",)]) == set(
        [((), "b.rst"), (("sub1",), "c.rst")]
    )
