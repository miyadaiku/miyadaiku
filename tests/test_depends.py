from conftest import SiteRoot
from miyadaiku import depends


def test_update(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "file1.rst",
        """
:jinja:`{{ page.link_to("./file2.rst") }}`
""",
    )
    siteroot.write_text(
        siteroot.contents / "file2.rst",
        """
""",
    )

    site = siteroot.load({"themes": ["package1"]}, {})

    ok, err, deps = site.build()
    depends.save_deps(site, deps)

    # test no-update
    site.load(site.root, {})
    rebuild, updated = depends.check_depends(site)

    assert rebuild is False
    assert updated == set()

    # test update
    (siteroot.contents / "file1.rst").write_text("")
    site.load(site.root, {})
    rebuild, updated = depends.check_depends(site)

    assert rebuild is False
    assert updated == set((((), "file1.rst"),))


def test_refs(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.contents / "file1.rst",
        """

:jinja:`{{ page.link_to("./file2.rst") }}`

""",
    )
    siteroot.write_text(
        siteroot.contents / "file2.rst",
        """
""",
    )

    site = siteroot.load({}, {})

    ok, err, deps = site.build()
    depends.save_deps(site, deps)

    # test update depends
    (siteroot.contents / "file2.rst").write_text("")
    site.load(site.root, {})
    rebuild, updated = depends.check_depends(site)

    assert rebuild is False
    assert updated == set((((), "file1.rst"), ((), "file2.rst"),))


def test_rebuild(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.contents / "file1.rst", "")
    siteroot.write_text(siteroot.contents / "file2.rst", "")

    site = siteroot.load({}, {})

    ok, err, deps = site.build()
    depends.save_deps(site, deps)

    # test new file
    (siteroot.contents / "file3.rst").write_text("")
    site.load(site.root, {})
    rebuild, updated = depends.check_depends(site)

    assert rebuild is True


def test_metadata(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.contents / "file1.rst", "")
    siteroot.write_text(siteroot.contents / "file2.rst", "")

    site = siteroot.load({}, {})

    ok, err, deps = site.build()
    depends.save_deps(site, deps)

    # test metadata changed
    (siteroot.contents / "file1.rst").write_text(
        """
file1-new-title
----------------------------
"""
    )
    site.load(site.root, {})
    rebuild, updated = depends.check_depends(site)

    assert rebuild is True


def test_macro(siteroot: SiteRoot) -> None:
    siteroot.write_text(siteroot.contents / "file1.rst", "")
    site = siteroot.load({}, {})

    ok, err, deps = site.build()
    depends.save_deps(site, deps)

    # test macro
    (siteroot.modules / "file1.rst").write_text(
        """
file1-new-title
----------------------------
"""
    )
