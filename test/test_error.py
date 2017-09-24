import pytest
from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, main
from miyadaiku.scripts.muneage import load_hook, build
import yaml


IS_DEBUG = pytest.mark.parametrize("is_debug", [
    (True,),
    (False,)])


@IS_DEBUG
def test_error_jinjastr(is_debug, sitedir, capsys):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''
test
----
.. jinja::

   {{1/0}}

''')

    build(sitedir, {}, False, debug=is_debug)
    out, err = capsys.readouterr()
    assert 'ZeroDivisionError: division by zero' in err


@IS_DEBUG
def test_error_str_jinjasyntax(is_debug, sitedir, capsys):

    (sitedir / 'contents/index.rst').write_text('''
test
----
.. jinja::

   {{(}}

''')

    build(sitedir, {}, False, debug=is_debug)
    out, err = capsys.readouterr()
    assert 'TemplateSyntaxError' in err
    assert '>>> {{(}}' in err


@IS_DEBUG
def test_error_templ(is_debug, sitedir, capsys):

    (sitedir / 'contents/index.rst').write_text('''
test
----
''')

    (sitedir / 'templates/page_article.html').write_text('''

{{1/0}}
''')

    build(sitedir, {}, False, debug=is_debug)
    out, err = capsys.readouterr()
    assert 'ZeroDivisionError: division by zero' in err
    print(err)


@IS_DEBUG
def test_error_templ_syntax(is_debug, sitedir, capsys):

    (sitedir / 'contents/index.rst').write_text('''
test
----
''')

    (sitedir / 'templates/page_article.html').write_text('''

{%}
''')

    build(sitedir, {}, False, debug=is_debug)
    out, err = capsys.readouterr()
    assert 'TemplateSyntaxError: page_article.html' in err
    print(err)
