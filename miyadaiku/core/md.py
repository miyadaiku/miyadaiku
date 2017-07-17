import re
import datetime
import dateutil.parser
import markdown
from markdown import util, preprocessors
import markdown.extensions.codehilite


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


class Ext(markdown.Extension):
    def extendMarkdown(self, md, globals):
        md.preprocessors.add('jinja',
                             JinjaPreprocessor(md),
                             "<normalize_whitespace")


class JinjaPreprocessor(preprocessors.Preprocessor):
    def run(self, lines):
        meta = {}
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

        self.markdown.meta = meta

        text = "\n".join(lines[n:])

        while True:
            m = re.search(r':jinja:`.*?(?<!\\)`', text)
            if not m:
                break
            placeholder = self.markdown.htmlStash.store(m[0], safe=True)
            text = '%s\n%s\n%s' % (text[:m.start()],
                                   placeholder,
                                   text[m.end():])

        text = text.translate({ord('{'): '&#123;', ord('}'): '&#125;'})
        return text.split("\n")


def load(path):
    return load_string(path.read_text(encoding='utf-8'))


def load_string(string):
    extensions = [
        Ext(),
        markdown.extensions.codehilite.CodeHiliteExtension(guess_lang=False),
        'markdown.extensions.extra',
    ]

    md = markdown.Markdown(extensions=extensions)
    html = md.convert(string)
    return md.meta, html
