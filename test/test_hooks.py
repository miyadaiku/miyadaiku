from pathlib import Path
from miyadaiku.core import rst, contents, config, jinjaenv, main
from miyadaiku.scripts.muneage import load_hook, build
import yaml


def test_build_depend(sitedir):

    hook = '''
from miyadaiku.core.hooks import *
import os
import __main__

seen = set()
__main__.seen_test_build_depend = seen

@start
def start(dirname, props):
    seen.add('start')

    assert dirname.is_dir()
    assert isinstance(props, dict)

@finished
def finished(dirname, props, site):
    seen.add('finished')

@pre_load
def pre_load(site, filename, package):
    assert site
    seen.add('pre_load')

@post_load
def post_load(site, filename, package, content):
    assert site
    seen.add('post_load')

@pre_build
def pre_build(site, content, output_path):
    assert site
    seen.add('pre_build')

@post_build
def post_build(site, content, output_path, files):
    assert site
    seen.add('post_build')

'''

    (sitedir / 'hooks.py').write_text(hook)
    content = sitedir / 'contents'
    content.joinpath('index.rst').write_text('''
test
----
''')
    load_hook(sitedir)
    build(sitedir, {}, debug=True)

    import __main__
    assert len(__main__.seen_test_build_depend) == 6
