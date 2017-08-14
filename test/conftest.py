import pytest
import pathlib


import miyadaiku.core.main  # install pyyaml converter


@pytest.fixture
def sitedir(tmpdir):
    d = tmpdir.mkdir('site')
    d.mkdir('contents')
    d.mkdir('templates')
    return pathlib.Path(str(d))
