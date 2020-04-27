import pytest

from conftest import SiteRoot
from miyadaiku import hook


def test_hook(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.path / "hooks.py",
        """
from miyadaiku.hook import *

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

    hook.load_hook(siteroot.path)
    site = siteroot.load({}, {})
    hook.run_start()
    hook.run_finished(site)

    assert len(hook.hooks_started) == 2
    assert [1, 1] == [f.called for f in hook.hooks_started]  # type: ignore

    assert len(hook.hooks_finished) == 2
    assert [1, 1] == [
        f.called for f in hook.hooks_finished  # type: ignore
    ]

    assert len(hook.hooks_initialized) == 1
    assert hook.hooks_initialized[0].called == 1  # type: ignore


def test_load(siteroot: SiteRoot) -> None:
    siteroot.write_text(
        siteroot.path / "hooks.py",
        """
from miyadaiku.hook import *

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

    hook.load_hook(siteroot.path)
    site = siteroot.load({}, {})

    root1 = site.files.get_content(((), "root1.txt"))
    assert root1.src.metadata["title"] == "hook_prehook_post"

    assert 1 == hook.hooks_load_finished[0].called  # type: ignore


@pytest.mark.parametrize("debug", [True, False])  # type: ignore
def test_build(siteroot: SiteRoot, debug: bool) -> None:
    siteroot.write_text(
        siteroot.path / "hooks.py",
        """
from miyadaiku.hook import *

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

    hook.load_hook(siteroot.path)
    site = siteroot.load({}, {}, debug=debug)
    site.build()

    assert len(hook.hooks_pre_build) == 1
    assert len(hook.hooks_post_build) == 1

    assert b"pre_buildpost_build1" == (siteroot.outputs / "root1.txt").read_bytes()
