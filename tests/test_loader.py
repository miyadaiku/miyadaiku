import pprint
from typing import Set, List
from pathlib import Path
from miyadaiku import ContentSrc, config, loader, site


def test_walk_directory(sitedir):
    dir1 = sitedir / "dir1"
    dir1.mkdir()

    dir2 = dir1 / "dir2"
    dir2.mkdir()

    file1 = dir1 / "file1"
    file1.write_text("")

    file11 = dir1 / "file1.props.yml"
    file11.write_text("name: value")

    file2 = dir2 / "file2"
    file2.write_text("")

    (dir1 / "test.bak").write_text("")

    results = loader.walk_directory(sitedir, set(["*.bak"]))
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


def test_walkpackage(sitedir):
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


def test_loadfiles(sitedir: Path):
    contentsdir = sitedir / "contents"
    filesdir = sitedir / "files"

    (sitedir / "config.yml").write_text(
        """
themes: 
    - package3
project_prop: value
"""
    )

    contentsdir.mkdir(exist_ok=True)
    (contentsdir / "root1.yml").write_text("root_prop: root_prop_value")
    (contentsdir / "root1.txt").write_text("content_root1")
    (contentsdir / "root_content1.txt").write_text("root_content1")

    filesdir.mkdir(exist_ok=True)
    (filesdir / "root1.txt").write_text("file_root1")
    (filesdir / "root_file1.txt").write_text("root_file1")

    files = loader.ContentFiles()
    cfg = config.Config({})
    root = sitedir
    ignores: Set[str] = set()
    themes = ["package3", "package4"]

    loader.loadfiles(files, cfg, root, ignores, themes)

    assert len(files._contentfiles) == 7
    assert files._contentfiles[((), "root1.txt")].get_body() == b"content_root1"
    assert files._contentfiles[((), "root_content1.txt")].get_body() == b"root_content1"
    assert files._contentfiles[((), "root_file1.txt")].get_body() == b"root_file1"

    assert (
        files._contentfiles[((), "package3_root.rst")].get_body().strip()
        == b"<p>package3/contents/package3_root.rst</p>"
    )
    assert (
        files._contentfiles[((), "package_root.rst")].get_body().strip()
        == b"<p>package3/contents/package_root.rst</p>"
    )
    assert (
        files._contentfiles[((), "package3_files_1.rst")].get_body().strip()
        == b"package3/files/package3_file_1.rst"
    )

    assert (
        files._contentfiles[((), "package4_root.rst")].get_body().strip()
        == b"<p>package4/contents/package4_root.rst</p>"
    )

    assert cfg.get((), "root_prop") == "root_prop_value"
    assert cfg.get((), "package3_prop_a1") == "value_package3_a1"


def test_get_contents(sitedir: Path):
    contentsdir = sitedir / "contents"
    contentsdir.mkdir(exist_ok=True)
    (contentsdir / "a.rst").write_text(
        """
.. article::
   :date: 2017-01-01
   :category: A
   :tags: tag1, tag2
   :prop1: propvalue1
test
"""
    )

    (contentsdir / "b.rst").write_text(
        """
.. article::
   :date: 2017-01-02
   :category: B
   :tags: tag1, tag3

test
"""
    )

    sub1 = contentsdir / "sub1"
    sub1.mkdir(exist_ok=True)
    (sub1 / "c.rst").write_text(
        """
.. article::
   :date: 2017-01-03
   :category: C
   :tags: tag2, tag3

test
"""
    )

    s = site.Site()
    s.load(sitedir, {})

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
