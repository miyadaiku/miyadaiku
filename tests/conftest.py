# type: ignore

import pytest
import pathlib
from typing import Any

# import miyadaiku

# miyadaiku.core.SHOW_TRACEBACK = True
# miyadaiku.core.DEBUG = True


@pytest.fixture
def sitedir(tmpdir: Any) -> pathlib.Path:
    d = tmpdir.mkdir("site")
    d.mkdir("modules")
    d.mkdir("contents")
    d.mkdir("templates")
    return pathlib.Path(str(d))
