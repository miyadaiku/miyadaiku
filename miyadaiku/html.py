# type: ignore

from typing import Tuple, Dict
import re
from miyadaiku import ContentSrc


def load(src: ContentSrc) -> Tuple[Dict, str]:
    return load_string(src.read_text())


def load_string(string):
    meta = {
        "type": "article",
        "has_jinja": True
    }
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
