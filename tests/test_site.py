import pprint
from typing import Set
from pathlib import Path
from miyadaiku.site import Site


def test_site(sitedir: Path):
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

    filesdir.mkdir(exist_ok=True)
    (filesdir / "root1.txt").write_text("file_root1")

    site = Site()
    site.load(sitedir, {'prop':'prop_value'})


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



