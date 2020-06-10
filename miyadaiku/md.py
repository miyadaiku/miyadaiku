from typing import Tuple, Dict, Any, Union
from pathlib import Path
import re
from collections import OrderedDict

import markdown
from markdown import util, preprocessors, postprocessors, blockprocessors
import markdown.extensions.codehilite
from miyadaiku import ContentSrc

HTML_PLACEHOLDER2 = util.STX + "jgnkfkaj:%s" + util.ETX

class HtmlStash2(util.HtmlStash):
    def get_placeholder(self, key):
        return HTML_PLACEHOLDER2 % key

class Ext(markdown.Extension):  # type: ignore
    def extendMarkdown(self, md):  # type: ignore
        # prior to fenced_code_block
        md.htmlStash2 = HtmlStash2()
        md.preprocessors.register(JinjaPreprocessor(md), "jinja", 27.5)
        #        md.preprocessors.add('jinja',
        #                             JinjaPreprocessor(md),
        #                             ">normalize_whitespace")

        # top priority
        md.parser.blockprocessors.register(TargetProcessor(md.parser), "target", 110)


#        md.parser.blockprocessors.add('target',
#                                      TargetProcessor(md.parser),
#                                      '_begin')


class JinjaPreprocessor(preprocessors.Preprocessor):  # type: ignore
    def run(self, lines):  # type: ignore
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
            self.md.meta[name] = value

        text = "\n".join(lines[n:])
        while True:
            m = re.search(r"(\\)?:jinja:`(.*?(?<!\\))`", text, re.DOTALL)
            if not m:
                break
            if m[1]:
                # escaped
                placeholder = self.md.htmlStash2.store(m[0])
            else:
                placeholder = self.md.htmlStash2.store(m[2])

            text = "%s%s%s" % (text[: m.start()], placeholder, text[m.end(0) :])

        return text.split("\n")


class JinjaPostprocessor(postprocessors.Postprocessor):  # type: ignore
    def run(self, text):

        text = text.translate({ord("{"): "&#123;", ord("}"): "&#125;"})

        """ Iterate over html stash and restore html. """
        replacements = OrderedDict()
        for i in range(self.md.htmlStash2.html_counter):
            html = self.md.htmlStash2.rawHtmlBlocks[i]
            placefolder = self.md.htmlStash2.get_placeholder(i)
            replacements["<p>%s</p>" % (placefolder )] = html + "\n"
            replacements[placefolder] = html

        if replacements:
            pattern = re.compile("|".join(re.escape(k) for k in replacements))
            return pattern.sub(lambda m: replacements[m.group(0)], text)
        else:
            return text


class TargetProcessor(blockprocessors.BlockProcessor):  # type: ignore

    RE = re.compile(r"^.. target::\s*([-a-zA-Z0-9_]+)\s*$")

    def test(self, parent, block):  # type: ignore
        return self.RE.search(block)

    def run(self, parent, blocks):  # type: ignore
        block = blocks.pop(0)
        m = self.RE.match(block)
        assert m
        attrs = {
            "class": "header_target",
            "id": m.group(1),
        }
        util.etree.SubElement(parent, "div", attrib=attrs)


def load(src: Union[ContentSrc, Path]) -> Tuple[Dict[str, Any], str]:
    s = src.read_text()
    return load_string(s)


def load_string(string: str) -> Tuple[Dict[str, Any], str]:
    extensions = [
        markdown.extensions.codehilite.CodeHiliteExtension(
            css_class="highlight", guess_lang=False
        ),
        "markdown.extensions.extra",
        Ext(),
    ]

    md = markdown.Markdown(extensions=extensions)
    md.postprocessors.register(JinjaPostprocessor(md), 'jinja_raw_html', 0)
    md.meta = {"type": "article", "has_jinja": True}
    html = md.convert(string)
    return md.meta, html
