from pathlib import Path
from miyadaiku import config


def test_load(sitedir):
    cfgfile = sitedir / 'config1.yml'
    cfgfile.write_text("""
themes:
   - tests.package1

prop1: prop1vaue
""")

    cfg = config.load(cfgfile)
    themes = config.load_themes(cfg)
    assert themes == ['tests.package1', 'tests.package2']
    assert cfg.get((), 'prop1') == 'prop1vaue'
    assert cfg.get((), 'package1_prop1') == 'package1_prop1_value'
    assert cfg.get((), 'package2_prop1') == 'package2_prop1_value'


def test_get():
    cfg = config.Config({})
    cfg.add(('dir1',), {'prop_a1': 'value_a1'})
    cfg.add(('dir1',), {'prop_b1': 'value_b1'})
    cfg.add(('dir1', 'dir2'), {'prop_a1': 'value_a11'})

    assert cfg.get(('dir1',), 'prop_a1') == 'value_a1'
    assert cfg.get(('dir1', 'dir2'), 'prop_a1') == 'value_a11'
    assert cfg.get(('dir1', 'dir2', ), 'prop_b1') == 'value_b1'
