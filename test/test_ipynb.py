from pathlib import Path
from miyadaiku.core import ipynb
DIR = Path(__file__).parent


def test_load():
    metadata, text = ipynb.load(DIR / 'test.ipynb')
    assert metadata['type'] == 'article'
#    print(text)
