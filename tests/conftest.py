# type: ignore

import pytest
import pathlib
from typing import Any

import logging

logging.getLogger().setLevel(logging.DEBUG)

# import miyadaiku

# miyadaiku.core.SHOW_TRACEBACK = True
# miyadaiku.core.DEBUG = True


@pytest.fixture
def sitedir(tmpdir: Any) -> pathlib.Path:
    d = tmpdir.mkdir("site")
    d.mkdir("modules")
    d.mkdir("contents")
    d.mkdir("files")
    d.mkdir("templates")
    return pathlib.Path(str(d))
