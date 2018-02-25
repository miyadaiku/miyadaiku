import pytest
from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, main
from miyadaiku.scripts.muneage import load_hook, build
import yaml

import logging
logging.basicConfig(level=logging.DEBUG)

IS_DEBUG = pytest.mark.parametrize("is_debug", [
    (True,),
    (False,)])


@IS_DEBUG
def test_error_jinjastr(is_debug, sitedir, caplog):
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''
test
----
.. jinja::

   {{1/0}}

''')

    build(sitedir, {}, False, debug=is_debug)
    assert 'ZeroDivisionError: division by zero' in caplog.text


@IS_DEBUG
def test_error_str_jinjasyntax(is_debug, sitedir, caplog):

    (sitedir / 'contents/index.rst').write_text('''
test
----
.. jinja::

   {{(}}

''')

    build(sitedir, {}, False, debug=is_debug)
    assert 'TemplateSyntaxError' in caplog.text
    assert '>>> {{(}}' in caplog.text


@IS_DEBUG
def test_error_templ(is_debug, sitedir, caplog):

    (sitedir / 'contents/index.rst').write_text('''
test
----
''')

    (sitedir / 'templates/page_article.html').write_text('''

{{1/0}}
''')

    build(sitedir, {}, False, debug=is_debug)
    assert 'ZeroDivisionError: division by zero' in caplog.text
    print(caplog.text)


@IS_DEBUG
def test_error_templ_syntax(is_debug, sitedir, caplog):

    (sitedir / 'contents/index.rst').write_text('''
test
----
''')

    (sitedir / 'templates/page_article.html').write_text('''

{%}
''')

    build(sitedir, {}, False, debug=is_debug)
    assert 'TemplateSyntaxError: page_article.html' in caplog.text
    print(caplog.text)
