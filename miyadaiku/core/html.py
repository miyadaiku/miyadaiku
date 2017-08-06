import re
import datetime
import dateutil.parser


def load(path):
    return load_string(path.read_text(encoding='utf-8'))


def load_string(string):
    meta = {}
    lines = string.splitlines()

    n = 0
    for l in lines:
        if not l.strip():
            n += 1
            continue
        m = re.match(r'([a-zA-Z0-9_-]+):\s(.+)$', l)
        if not m:
            break
        n += 1

        name, value = m[1].strip(), m[2].strip()
        meta[name] = value

    if 'type' not in meta:
        meta['type'] = 'article'

    return meta, '\n'.join(lines[n:])
