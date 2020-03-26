import datetime
from miyadaiku import config




def test_get():
    cfg = config.Config({'root': 'root_value'})

    cfg.add(("dir1",), {"prop_a1": "value_a1"})
    cfg.add(("dir1",), {"prop_b1": "value_b1"})
    cfg.add(("dir1", "dir2"), {"prop_a1": "value_a11"})

    assert cfg.get(("dir1",), "prop_a1") == "value_a1"
    assert cfg.get(("dir1", "dir2"), "prop_a1") == "value_a11"
    assert cfg.get(("dir1", "dir2",), "prop_b1") == "value_b1"

    assert cfg.get(("dir1", "dir2",), "root") == 'root_value'

def test_theme():
    cfg = config.Config({'root': 'root_value'})
    cfg.add_themecfg({'theme': 'theme_value'})

    assert cfg.get(("dir1", "dir2",), "theme") == 'theme_value'


def test_value():
    cfg = config.Config({
        'site_url': 'http://localhost',
        'draft': 'false',
        'tags': 'tag1, tag2',
        'date': '2020-01-01 00:00:00',
        'order': '100'
    })

    assert(cfg.get((), 'site_url') == 'http://localhost/')
    assert(cfg.get((), 'draft') == False)
    assert(cfg.get((), 'tags') ==  ['tag1', 'tag2'])
    assert(cfg.get((), 'date') ==  datetime.datetime(2020,1,1,0,0,0))
    assert(cfg.get((), 'order') ==  100)
