import logging
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from . import ContentSrc

logger = logging.getLogger(__name__)

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
            if not isinstance(d, dict):
                logger.warn("yaml should return dicionay: %s", meta)
                return {}, s
            return d, "\n".join(lines[n + 1 :])

    return {}, s


def replace_jinjatag(text: str, repl: Optional[Callable[[str], str]] = None,) -> str:

    re_start = re.compile(r"(\\)?:jinja:`")
    re_end = re.compile(r"\\|`")

    pos = 0
    ret = ""

    while True:
        # find :jinja:`
        m = re_start.search(text, pos)
        if not m:
            break

        start, end = m.span()
        ret += text[pos:start]

        if m[1]:
            # skip \:jinja:
            ret += text[start + 1 : end]
            pos = end
            continue

        expr = ""
        pos = end
        while True:
            # find `
            m = re_end.search(text, pos)
            if not m:
                ret += text[start:]
                pos = len(text)
                break

            expr_start, expr_end = m.span()
            expr += text[pos:expr_start]

            if m[0] == "\\":
                expr += text[expr_start + 1 : expr_end + 1]
                pos = expr_end + 1
                continue
            else:
                # m[0] == '`'
                if repl:
                    expr = repl(expr)
                ret += expr
                pos = expr_end
                break

    if pos != len(text):
        ret += text[pos:]

    return ret
