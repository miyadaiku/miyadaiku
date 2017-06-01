import pytest
import pathlib

@pytest.fixture(scope='session')
def sitedir(tmpdir_factory):
    d = tmpdir_factory.mktemp('site')
    d.mkdir('contents')
    return pathlib.Path(str(d))

