import pytest
import pathlib

import miyadaiku.core
import miyadaiku.core.site  # install pyyaml converter

#miyadaiku.core.SHOW_TRACEBACK = True
#miyadaiku.core.DEBUG = True


@pytest.fixture
def sitedir(tmpdir):
    d = tmpdir.mkdir('site')
    d.mkdir('contents')
    d.mkdir('templates')
    return pathlib.Path(str(d))
