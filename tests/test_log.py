from typing import cast, List, Any
from unittest.mock import patch
from miyadaiku import builder, mp_log
from conftest import SiteRoot


@patch('miyadaiku.builder.logger.log')
def test_mpbuild(log:Any, siteroot: SiteRoot) -> None:
    mp_log.init_logging()
    siteroot.write_text(siteroot.templates / "page_article.html",
        """
{{ abcdefg }}
""",
    )

    siteroot.write_text(siteroot.contents / "test.html", "test")

    site = siteroot.load({}, {})
    site.build()
    args, kwargs = log.call_args_list[0]

    assert str(siteroot.contents / "test.html") in kwargs['extra']['msgdict']['msg']