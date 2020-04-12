from miyadaiku import to_contentpath


def test_to_contentpath() -> None:
    assert ((), "filename.txt") == to_contentpath("filename.txt")
