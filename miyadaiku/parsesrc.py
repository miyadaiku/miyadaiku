from typing import Any, Dict, List, Tuple
import yaml
import re
from . import ContentSrc

SEP = re.compile(r"^%%%+\s+(\S.*)$(\n)?", re.M)


def splitsrc(src: ContentSrc, text: str) -> List[Tuple[ContentSrc, str]]:
    matches = list(SEP.finditer(text))
    if not matches:
        return [(src, text)]

    if matches[0].start() != 0:
        return [(src, text)]

    starts = [m.end() for m in matches]
    ends = [m.start() for m in matches[1:]] + [len(text)]
    filenames = [m[1].strip() for m in matches]

    ret = []
    for start, end, filename in zip(starts, ends, filenames):
        s = src.copy()
        path = (s.contentpath[0], filename)
        s = s._replace(contentpath=path)
        ret.append((s, text[start:end]))
    return ret


def split_yaml(s: str, sep: str) -> Tuple[Dict[Any, Any], str]:
    lines = s.split("\n")
    if len(lines) <= 2:
        return {}, s

    if not lines[0].startswith(sep):
        return {}, s

    for n, line in enumerate(lines[1:], 1):
        if line.startswith(sep):
            meta = "\n".join(lines[1:n])
            d = yaml.load(meta, Loader=yaml.FullLoader,) or {}
            return d, "\n".join(lines[n + 1 :])

    return {}, s
