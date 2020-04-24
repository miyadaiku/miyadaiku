from typing import cast, List, Any
import traceback
from unittest.mock import patch
import pytest

from miyadaiku import builder, mp_log, context, exceptions
from conftest import SiteRoot, create_contexts


@patch("miyadaiku.builder.logger.log")
def test_mpbuild(log: Any, siteroot: SiteRoot) -> None:
    mp_log.init_logging()
    siteroot.write_text(
        siteroot.templates / "page_article.html",
        """
{{ page.html }}
""",
    )

    siteroot.write_text(siteroot.contents / "test.html", "test")

    site = siteroot.load({}, {})
    site.build()
    args, kwargs = log.call_args_list[0]

    assert str(siteroot.contents / "test.html") in kwargs["extra"]["msgdict"]["msg"]



def test_jinja_str_err(siteroot: SiteRoot):
    (ctx,) = create_contexts(siteroot, srcs=[("abc/index.rst", "",)],)
    env = ctx.site.build_jinjaenv()

    src = '''1
2
3
{{ 1/0 }}
4
5
6
'''

    try:
        context.eval_jinja(ctx, ctx.content, 'propname', src, {})
    except exceptions.JinjaEvalError as e:
        assert e.errors[0][1] == 4
        print(e.errors)
        assert '>>> {{ 1/0 }}' in e.errors[0][2]
    else:
        assert False

def test_jinja_str_syntaxerr(siteroot: SiteRoot):
    (ctx,) = create_contexts(siteroot, srcs=[("abc/index.rst", "",)],)
    env = ctx.site.build_jinjaenv()

    src = '''1
2
3
{{ @ }}
4
5
6
'''

    try:
        context.eval_jinja(ctx, ctx.content, 'propname', src, {})
    except exceptions.JinjaEvalError as e:
        assert e.errors[0][1] == 4
        assert '>>> {{ @ }}' in e.errors[0][2]
    else:
        assert False


def test_jinja_templ_err(siteroot: SiteRoot):
    mp_log.init_logging()
    siteroot.write_text(siteroot.templates / "page_article.html",
        """1
2
{{ abc }}
3
4
5
""",
    )

    siteroot.write_text(siteroot.contents / "test.html", "test")

    site = siteroot.load({}, {})
    jinjaenv = site.build_jinjaenv()
    ctx = context.JinjaOutput(site, jinjaenv, ((), "test.html"))

    try:
        context.eval_jinja_template(ctx, ctx.content, 'page_article.html', {})
    except exceptions.JinjaEvalError as e:
        assert e.errors[0][1] == 3
        assert '>>> {{ abc }}' in e.errors[0][2]
    else:
        assert False
    
def test_jinja_templ_syntaxerr(siteroot: SiteRoot):
    mp_log.init_logging()
    siteroot.write_text(siteroot.templates / "page_article.html",
        """1
2
{{ @ }}
3
4
5
""",
    )

    siteroot.write_text(siteroot.contents / "test.html", "test")

    site = siteroot.load({}, {})
    jinjaenv = site.build_jinjaenv()
    ctx = context.JinjaOutput(site, jinjaenv, ((), "test.html"))

    try:
        context.eval_jinja_template(ctx, ctx.content, 'page_article.html', {})
    except exceptions.JinjaEvalError as e:
        assert e.errors[0][1] == 3
        assert '>>> {{ @ }}' in e.errors[0][2]
    else:
        assert False
    

def test_jinja_err_both(siteroot: SiteRoot):
    (ctx,) = create_contexts(siteroot, srcs=[("abc/index.rst", """

.. jinja::
   12345
   {{ = }}
   <a><b>

""",)],)

    with pytest.raises(exceptions.JinjaEvalError) as excinfo:
        ctx.build()

    e = excinfo.value
    assert len(e.errors) == 2
    assert '>>>     {{ page.html }}' in e.errors[0][2]
    assert '>>> {{ = }}' in e.errors[1][2]
