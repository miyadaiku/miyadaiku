import re
import datetime
import dateutil.parser


def date(v):
    v = v.strip()
    if v:
        ret = dateutil.parser.parse(v)
        if isinstance(ret, datetime.time):
            raise ValueError(f'String does not contain a date: {v!r}')
        return ret


def tags(v):
    return [t.strip() for t in v.split(',')]


def draft(v):
    v = v.strip().lower()
    if not v:
        return False

    if v in {'yes', 'true'}:
        return True
    elif v in {'no', 'false'}:
        return False

    raise ValueError("Invalid boolean value: %s" % v)


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
        if name == 'date':
            value = date(value)
        elif name == 'tags':
            value = tags(value)
        elif name == 'draft':
            value = draft(value)

        meta[name] = value

    if 'type' not in meta:
        meta['type'] = 'article'

    return meta, '\n'.join(lines[n:])
