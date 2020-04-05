from pathlib import Path
from miyadaiku import ipynb

DIR = Path(__file__).parent


def test_load() -> None:
    metadata, text = ipynb.load(DIR / "test.ipynb")
    assert metadata["type"] == "article"
    print(text)
