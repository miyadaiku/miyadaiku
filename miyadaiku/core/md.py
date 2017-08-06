import re
import datetime
import dateutil.parser
import markdown
from markdown import util, preprocessors, postprocessors, blockprocessors
import markdown.extensions.codehilite


class Ext(markdown.Extension):
    def extendMarkdown(self, md, globals):
        md.preprocessors.add('jinja',
                             JinjaPreprocessor(md),
                             ">normalize_whitespace")

        md.parser.blockprocessors.add('target',
                                      TargetProcessor(md.parser),
                                      '_begin')


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
            meta[name] = value

        if 'type' not in meta:
            meta['type'] = 'article'

        self.markdown.meta = meta

        text = "\n".join(lines[n:])
        while True:
            m = re.search(r'(\\)?:jinja:`(.*?(?<!\\))`', text, re.DOTALL)
            if not m:
                break
            if m[1]:
                # escaped
                placeholder = self.markdown.htmlStash.store(m[0], safe=True)
            else:
                placeholder = self.markdown.htmlStash.store(m[2], safe=True)

            text = '%s%s%s' % (text[:m.start()],
                               placeholder,
                               text[m.end(0):])

        text = text.translate({ord('{'): '&#123;', ord('}'): '&#125;'})
        return text.split("\n")


class JinjaRawHtmlPostprocessor(postprocessors.RawHtmlPostprocessor):
    def run(self, text):
        while True:
            ret = super().run(text)
            if ret == text:
                # all stashes were restored
                break
            text = ret
        return ret

    def isblocklevel(self, html):
        if re.match(r'\{.*}$', html.strip(), re.DOTALL):
            return True
        return super().isblocklevel(html)


# patch postprocessors.RawHtmlPostprocessor
postprocessors.RawHtmlPostprocessor = JinjaRawHtmlPostprocessor


class TargetProcessor(blockprocessors.BlockProcessor):

    RE = re.compile(r'^.. target::\s*([-a-zA-Z0-9_]+)\s*$')

    def test(self, parent, block):
        return self.RE.search(block)

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.match(block)
        attrs = {
            'class': 'header_target',
            'id': m.group(1),
        }
        util.etree.SubElement(parent, 'div', attrib=attrs)


def load(path):
    return load_string(path.read_text(encoding='utf-8'))


def load_string(string):
    extensions = [
        markdown.extensions.codehilite.CodeHiliteExtension(guess_lang=False),
        'markdown.extensions.extra',
        Ext(),
    ]

    md = markdown.Markdown(extensions=extensions)
    html = md.convert(string)
    return md.meta, html
