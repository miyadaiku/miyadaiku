from typing import cast, List
from miyadaiku import builder
from conftest import SiteRoot


def test_index_group(siteroot: SiteRoot) -> None:
    for i in range(21):
        tag = f"tag{i % 2 + 1}"
        siteroot.write_text(
            siteroot.contents / f"htmldir/{i}.html",
            f"""
tags: {tag}

html{i} - tag: {tag}
""",
        )

    siteroot.write_text(
        siteroot.contents / "htmldir/index.yml",
        """
type: index
groupby: tags
""",
    )

    site = siteroot.load({}, {})
    builders = builder.create_builders(
        site, site.files.get_content((("htmldir",), "index.yml"))
    )
    indexbuilders = cast(List[builder.IndexBuilder], builders)
    jinjaenv = site.build_jinjaenv()
    for b in indexbuilders:
        ctx = b.build_context(site, jinjaenv)
        (f,) = ctx.build()

    assert len(indexbuilders) == 4
    assert sum(len(b.items) for b in indexbuilders) == 21
