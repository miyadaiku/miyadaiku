from typing import Set, List, cast, Sequence, Tuple
import re
from pathlib import Path
from miyadaiku import ContentSrc, config, loader, site, context
from conftest import SiteRoot

def create_contexts(siteroot: SiteRoot, srcs: Sequence[Tuple[str, str]])->List[context.JinjaOutput]:
    for path, src in srcs:
        siteroot.write_text(siteroot.contents / path, src)

    site = siteroot.load({}, {})
    ret = []
    for path, src in srcs:
        ctx = context.JinjaOutput(site, loader.to_contentpath(path))
        ret.append(ctx)

    return ret


def test_get_abstract(siteroot: SiteRoot)->None:
    s = 'abcdefg' * 1
    body = f'<div>123<div>456<div>789<div>abc</div>def</div>ghi</div>jkl</div>'

    ctx, = create_contexts(siteroot, srcs=[("doc.html", body)])

    abstract = ctx.content.build_abstract(ctx, 2)
    txt = re.sub(r"<[^>]*>", "", abstract)
    assert len(txt) == 2

    abstract = ctx.content.build_abstract(ctx, 6)
    txt = re.sub(r"<[^>]*>", "", abstract)
    assert len(txt) == 6

    abstract = ctx.content.build_abstract(ctx, 14)
    txt = re.sub(r"<[^>]*>", "", abstract)
    assert len(txt) == 14

    abstract = ctx.content.build_abstract(ctx, 100)
    txt = re.sub(r"<[^>]*>", "", abstract)
    assert len(txt) == 21

def test_get_headers(siteroot: SiteRoot) -> None:

    ctx, = create_contexts(siteroot, srcs=[("doc.html", """
<h1>header1{{1+1}}</h1>
<div>body1</div>

<h2>header2{{2+2}}</h2>
<div>body2</div>
""")])

    headers = ctx.content.get_headers(ctx)

    assert headers == [context.HTMLIDInfo(id='h_header12', tag='h1', text='header12'), 
                       context.HTMLIDInfo(id='h_header24', tag='h2', text='header24')]


