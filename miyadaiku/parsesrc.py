from typing import Any, Dict, List, Tuple, Callable, Match, Optional
import yaml
import re
import logging
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


def replace_jinjatag(text: str, repl: Optional[Callable[[str], str]] = None) -> str:
    pos = 0
    ret = ''

    jinja = re.compile(r"(\\)?:jinja:`")
    tail = re.compile(r"(?<!\\)`")

    while True:
#        breakpoint()
#        print(pos)
        # find :jinja:`
        m = jinja.search(text, pos)
        if not m:
            break

        start, end = m.span()
        ret += text[pos:start]

        if m[1]:
            # skip \\
            ret += text[start+1:start+2]
            pos = start+2
            continue

        # find `
        m = tail.search(text, end)
        if not m:
            break

        expr_start, expr_end = m.span()
        expr = text[end:expr_start]

        if repl:
            expr = repl(expr)
    
        ret += expr
        pos = expr_end

    if pos != len(text):
        ret += text[pos:]


    return ret

#    def sub_jinja(m: Match[str]) -> str:
#        if m[1]:
#            # escaped (e.g. \:jinja:``)
#            return m[0][1:]
#        s = m[2]
#        if repl:
#            return repl(s)
#        else:
#            return s

#    text = re.sub(r"(\\)?:jinja:`(.*?(?<!\\))`", sub_jinja, text, flags=re.DOTALL)
#    return text
