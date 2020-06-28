from typing import Any, Dict, List, Tuple
import re
from miyadaiku import ContentSrc, parsesrc


def load(src: ContentSrc) -> List[Tuple[ContentSrc, str]]:
    meta, html = _load_string(src.read_text())
    src.metadata.update(meta)
    return [(src, html)]


def _load_string(string: str) -> Tuple[Dict[str, Any], str]:
    loaded, string = parsesrc.split_yaml(string, sep="---")

    meta = {"type": "article", "has_jinja": True}
    meta.update(loaded)

    lines = string.splitlines()

    n = 0
    for l in lines:
        if not l.strip():
            n += 1
            continue
        m = re.match(r"([a-zA-Z0-9_-]+):\s(.+)$", l)
        if not m:
            break
        n += 1

        name, value = m[1].strip(), m[2].strip()
        meta[name] = value

    return meta, "\n".join(lines[n:])
