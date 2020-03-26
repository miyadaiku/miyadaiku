import pprint
from typing import Set
from pathlib import Path
from miyadaiku import ContentSrc, loader, config


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

    (sitedir / "config.yml").write_text("""
themes: 
    - package3
project_prop: value
""")

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
    assert files._contentfiles[((), "root1.txt")][0].read_text() == "content_root1"
    assert files._contentfiles[((), "root_content1.txt")][0].read_text() == "root_content1"
    assert files._contentfiles[((), "root_file1.txt")][0].read_text() == "root_file1"

    assert files._contentfiles[((), "package3_root.rst")][0].read_text() == "package3/contents/package3_root.rst"
    assert files._contentfiles[((), "package_root.rst")][0].read_text() == "package3/contents/package_root.rst"
    assert files._contentfiles[((), "package3_files_1.rst")][0].read_text() == "package3/files/package3_file_1.rst"
    
    assert files._contentfiles[((), "package4_root.rst")][0].read_text() == "package4/contents/package4_root.rst"

    assert cfg.get((), 'root_prop') == "root_prop_value"
    assert cfg.get((), 'package3_prop_a1') == "value_package3_a1"



