import os
from typing import Any, Dict, List, Tuple

from miyadaiku import ContentSrc

from . import parsesrc


def load(src: ContentSrc) -> List[Tuple[ContentSrc, str]]:
    s = src.read_text()

    ret = []
    srces = parsesrc.splitsrc(src, s)
    for src, txt in srces:
        meta, html = _load_string(src, txt)
        src.metadata.update(meta)
        ret.append((src, html))

    return ret


def _load_string(src: ContentSrc, string: str) -> Tuple[Dict[str, Any], str]:
    ext = os.path.splitext(src.contentpath[1])[1]
    meta = {
        "type": "article",
        "has_jinja": False,
        "ext": ext,
        "article_template": "plain.txt",
        "loader": "text",
    }
    filemeta, string = parsesrc.split_yaml(string, sep="---")
    meta.update(filemeta)

    return meta, string
