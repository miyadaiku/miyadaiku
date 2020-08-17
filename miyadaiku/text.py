import os
import re
from collections import OrderedDict
from typing import Any, Dict, List, Tuple

import markdown
import markdown.extensions.codehilite
from markdown import blockprocessors, postprocessors, preprocessors, util

from miyadaiku import ContentSrc

from . import parsesrc

HTML_PLACEHOLDER2 = util.STX + "jgnkfkaj:%s" + util.ETX


class HtmlStash2(util.HtmlStash):  # type: ignore
    def get_placeholder(self, key):  # type: ignore
        return HTML_PLACEHOLDER2 % key


class Ext(markdown.Extension):  # type: ignore
    def extendMarkdown(self, md):  # type: ignore
        # prior to fenced_code_block
        md.htmlStash2 = HtmlStash2()
        md.preprocessors.register(JinjaPreprocessor(md), "jinja", 27.5)

        # top priority
        md.parser.blockprocessors.register(TargetProcessor(md.parser), "target", 110)


class JinjaPreprocessor(preprocessors.Preprocessor):  # type: ignore
    def run(self, lines):  # type: ignore
        n = 0
        for line in lines:
            if not line.strip():
                n += 1
                continue
            m = re.match(r"([a-zA-Z0-9_-]+):\s(.+)$", line)
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
    def run(self, text):  # type: ignore

        text = text.translate({ord("{"): "&#123;", ord("}"): "&#125;"})

        """ Iterate over html stash and restore html. """
        replacements = OrderedDict()
        for i in range(self.md.htmlStash2.html_counter):
            html = self.md.htmlStash2.rawHtmlBlocks[i]
            placefolder = self.md.htmlStash2.get_placeholder(i)
            replacements["<p>%s</p>" % (placefolder)] = html + "\n"
            replacements[placefolder] = html

        if replacements:
            pattern = re.compile("|".join(re.escape(k) for k in replacements))
            return pattern.sub(lambda m: replacements[m.group(0)], text)  # type: ignore
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


def load(src: ContentSrc) -> List[Tuple[ContentSrc, str]]:
    s = src.read_text()

    ret = []
    srces = parsesrc.splitsrc(src, s)
    for src, txt in srces:
        meta, html = _load_string(src, txt)
        src.metadata.update(meta)
        ret.append((src, html))

    return ret


def _load_string(src: ContentSrc, string: str) -> Tuple[Dict[str, Any], str]:
    ext = os.path.splitext(src.contentpath[1])[1]
    meta = {
        "type": "article",
        "has_jinja": True,
        "ext": ext,
        "article_template": "plain.txt",
    }
    filemeta, string = parsesrc.split_yaml(string, sep="---")
    meta.update(filemeta)

    return meta, string
