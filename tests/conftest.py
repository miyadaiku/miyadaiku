import pytest  # type: ignore
import pathlib

# import miyadaiku

# miyadaiku.core.SHOW_TRACEBACK = True
# miyadaiku.core.DEBUG = True


@pytest.fixture
def sitedir(tmpdir):
    d = tmpdir.mkdir("site")
    d.mkdir("modules")
    d.mkdir("contents")
    d.mkdir("templates")
    return pathlib.Path(str(d))
