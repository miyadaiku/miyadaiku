import pprint
from typing import Set
from pathlib import Path
from miyadaiku.site import Site


def test_site(sitedir: Path) -> None:
    contentsdir = sitedir / "contents"
    filesdir = sitedir / "files"

    (sitedir / "config.yml").write_text(
        """
themes: 
    - package3
project_prop: value
"""
    )

    (contentsdir / "root1.yml").write_text(
        """
root_prop: root_prop_value
generate_metadata_file: true
"""
    )
    (contentsdir / "root1.txt").write_text("content_root1")
    (contentsdir / "root2.rst").write_text("content_root2")

    filesdir.mkdir(exist_ok=True)
    (filesdir / "root1.txt").write_text("file_root1")

    site = Site()
    site.load(sitedir, {"prop": "prop_value"})

    assert not (contentsdir / "root.txt.props.yml").exists()
    assert (contentsdir / "root2.rst.props.yml").exists()

    assert len(site.files._contentfiles) == 6
    assert ((), "root1.txt") in site.files._contentfiles
    assert ((), "package_root.rst") in site.files._contentfiles
    assert ((), "package3_root.rst") in site.files._contentfiles
    assert ((), "package3_files_1.rst") in site.files._contentfiles
    assert ((), "package4_root.rst") in site.files._contentfiles

    assert site.config.get((), "prop") == "prop_value"
    assert site.config.get((), "root_prop") == "root_prop_value"
    assert site.config.get((), "package3_prop") == "package3_prop_value"
    assert site.config.get((), "package3_prop_a1") == "value_package3_a1"
    assert site.config.get((), "package4_prop") == "package4_prop_value"
