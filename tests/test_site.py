from conftest import SiteRoot


def test_site(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "root1.yml",
        """
root_prop: root_prop_value
generate_metadata_file: true
""",
    )
    siteroot.write_text(siteroot.contents / "root1.txt", "content_root1")
    siteroot.write_text(siteroot.contents / "root2.rst", "content_root2")
    siteroot.write_text(siteroot.files / "root1.txt", "file_root1")

    site = siteroot.load(
        {"themes": ["package3"], "root_prop": "root_prop_value"}, {"prop": "prop_value"}
    )

    assert not (siteroot.contents / "root1.txt.props.yml").exists()
    assert (siteroot.contents / "root2.rst.props.yml").exists()

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
