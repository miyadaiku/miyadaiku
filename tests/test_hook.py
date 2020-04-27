import pytest

from conftest import SiteRoot
from miyadaiku import extend


def test_hook(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.path / "hooks.py",
        """
from miyadaiku.extend import *

@started
def start():
    start.called = 1

@started
def start2():
    start2.called = 1


@finished
def fin(site):
    fin.called = 1

@finished
def fin2(site):
    fin2.called = 1


@initialized
def initialized(site):
    initialized.called = 1

""",
    )

    extend.load_hook(siteroot.path)
    site = siteroot.load({}, {})
    extend.run_start()
    extend.run_finished(site)

    assert len(extend.hooks_started) == 2
    assert [1, 1] == [f.called for f in extend.hooks_started]  # type: ignore

    assert len(extend.hooks_finished) == 2
    assert [1, 1] == [
        f.called for f in extend.hooks_finished  # type: ignore
    ]

    assert len(extend.hooks_initialized) == 1
    assert extend.hooks_initialized[0].called == 1  # type: ignore


def test_load(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.path / "hooks.py",
        """
from miyadaiku.extend import *

@pre_load
def pre_load1(site, contentsrc, binary):
    contentsrc.metadata['title'] = 'hook_pre'
    return contentsrc

@post_load
def post_load1(site, contentsrc, binary, bytes):
    contentsrc.metadata['title'] = contentsrc.metadata['title'] + 'hook_post'
    return contentsrc, bytes

@load_finished
def load_finished1(site):
    load_finished1.called = 1

""",
    )

    siteroot.write_text(siteroot.contents / "root1.txt", "content_root1")

    extend.load_hook(siteroot.path)
    site = siteroot.load({}, {})

    root1 = site.files.get_content(((), "root1.txt"))
    assert root1.src.metadata["title"] == "hook_prehook_post"

    assert 1 == extend.hooks_load_finished[0].called  # type: ignore


@pytest.mark.parametrize("debug", [True, False])  # type: ignore
def test_build(siteroot: SiteRoot, debug: bool) -> None:
    siteroot.write_text(
        siteroot.path / "hooks.py",
        """
from miyadaiku.extend import *

@pre_build
def pre_build1(ctx):
    ctx.content.body = b"pre_build"
    return ctx

@post_build
def post_build1(ctx, filenames):
    org = filenames[0].read_bytes()
    filenames[0].write_bytes(org+b"post_build1")
""",
    )

    siteroot.write_text(siteroot.contents / "root1.txt", "content_root1")

    extend.load_hook(siteroot.path)
    site = siteroot.load({}, {}, debug=debug)
    site.build()

    assert len(extend.hooks_pre_build) == 1
    assert len(extend.hooks_post_build) == 1

    assert b"pre_buildpost_build1" == (siteroot.outputs / "root1.txt").read_bytes()
