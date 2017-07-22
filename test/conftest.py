import pytest
import pathlib


@pytest.fixture
def sitedir(tmpdir):
    d = tmpdir.mkdir('site')
    d.mkdir('contents')
    return pathlib.Path(str(d))
