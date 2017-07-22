import pytest
import pathlib


@pytest.fixture
def sitedir(tmpdir):
    d = tmpdir.mkdir('site')
    d.mkdir('contents')
    d.mkdir('templates')
    return pathlib.Path(str(d))
