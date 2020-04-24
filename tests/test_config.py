import datetime
from miyadaiku import config


def test_get() -> None:
    cfg = config.Config({"root": "root_value"})

    cfg.add(("dir1",), {"prop_a1": "value_a1"})
    cfg.add(("dir1",), {"prop_b1": "value_b1"})
    cfg.add(("dir1", "dir2"), {"prop_a1": "value_a11"})

    assert cfg.get(("dir1",), "prop_a1") == "value_a1"
    assert cfg.get(("dir1", "dir2"), "prop_a1") == "value_a11"
    assert cfg.get(("dir1", "dir2",), "prop_b1") == "value_b1"

    assert cfg.get(("dir1", "dir2",), "root") == "root_value"


def test_add_str() -> None:
    cfg = config.Config({})
    cfg.add("/", {"root1": "value1"})
    assert cfg.get("/", "root1") == "value1"
    assert cfg.get((), "root1") == "value1"


def test_theme() -> None:
    cfg = config.Config({"root": "root_value"})
    cfg.add_themecfg({"theme": "theme_value"})

    assert cfg.get(("dir1", "dir2",), "theme") == "theme_value"


def test_value() -> None:
    cfg = config.Config(
        {
            "site_url": "http://localhost",
            "draft": "false",
            "tags": "tag1, tag2",
            "date": "2020-01-01 00:00:00",
            "order": "100",
        }
    )

    assert cfg.get((), "site_url") == "http://localhost/"
    assert not cfg.get((), "draft")
    assert cfg.get((), "tags") == ["tag1", "tag2"]
    assert cfg.get((), "date") == datetime.datetime(2020, 1, 1, 0, 0, 0)
    assert cfg.get((), "order") == 100


def test_import() -> None:
    cfg = config.Config({"imports": "a"})
    cfg.add(("dir1",), {"imports": "b"})
    cfg.add_themecfg({"imports": "c"})

    assert set(cfg.get(("dir1",), "imports")) == {"a", "b", "c"}
