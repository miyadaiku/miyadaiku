from pathlib import Path
from miyadaiku.core import config, contents, main

DIR = Path(__file__).parent
SITE = DIR / 'site1'


def test_config():
    cfg = config.Config(DIR / 'config1.yml')
    assert cfg.get((), 'prop1') == 'prop1vaue'
    assert cfg.get((), 'package1_prop1') == 'package1_prop1_value'
    assert cfg.get((), 'package2_prop1') == 'package2_prop1_value'


def test_prop():
    cfg = config.Config(DIR / 'config1.yml', {'prop1': 'XXX'})
    assert cfg.get((), 'prop1') == 'XXX'


def test_get():
    site = main.Site(Path(''))

    contents.load_directory(site, SITE / 'contents')
    contents.load_package(site, 'package1', 'contents')

    assert site.config.get(('dir1',), 'prop_a1') == 'value_site_a1'
    assert site.config.get(('dir1',), 'prop_b') == 'value_site_b'
    assert site.config.get(('dir1', 'dir2'), 'prop_a1') == 'value_b1'
    assert site.config.get(('dir1', 'dir2', 'dir3'), 'prop_a1') == 'value_b1'
