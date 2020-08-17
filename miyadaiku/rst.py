import collections
import html
import os
import re
from typing import Any, Dict, List, Tuple

import docutils
import docutils.core
import docutils.nodes
import docutils.utils
import docutils.writers.html5_polyglot
from bs4 import BeautifulSoup
from docutils.parsers.rst import Directive, directives, roles
from docutils.readers import standalone
from docutils.transforms import frontmatter

from miyadaiku import ContentSrc

from . import pygment_directive  # noqa


class _RstDirective(Directive):  # type: ignore
    def run(self) -> List[Any]:
        if "type" not in self.options:
            self.options["type"] = self.CONTENT_TYPE

        cur = getattr(self.state.document, "article_metadata", {})
        cur.update(self.options)
        self.state.document.article_metadata = cur
        return []


class ArticleDirective(_RstDirective):
    CONTENT_TYPE = "article"

    required_arguments = 0
    optional_arguments = 0

    # use defaultdict to pass undefined arguments.
    option_spec = collections.defaultdict(
        lambda: directives.unchanged,
        {
            "title": directives.unchanged,
            "draft": directives.unchanged,
            "date": directives.unchanged,
            "category": directives.unchanged,
            "tags": directives.unchanged,
            "template": directives.unchanged,
            "filename": directives.unchanged,
        },
    )


directives.register_directive("article", ArticleDirective)


class SnippetDirective(_RstDirective):
    CONTENT_TYPE = "snippet"
    required_arguments = 0
    optional_arguments = 0

    # use defaultdict to pass undefined arguments.
    option_spec = collections.defaultdict(
        lambda: directives.unchanged, {"title": directives.unchanged}
    )


directives.register_directive("snippet", SnippetDirective)


class jinjalit(docutils.nodes.Inline, docutils.nodes.TextElement):  # type: ignore
    pass


def jinja_role(role, rawtext, text, lineno, inliner, options={}, content=[]):  # type: ignore
    node = jinjalit(rawtext, docutils.utils.unescape(text, 1), **options)
    node.source, node.line = inliner.reporter.get_source_and_line(lineno)
    return [node], []


roles.register_local_role("jinja", jinja_role)


class JinjaDirective(Directive):  # type: ignore
    required_arguments = 0
    optional_arguments = 0
    has_content = True

    def run(self):  # type: ignore
        text = "\n".join(self.content)
        node = jinjalit(text, docutils.utils.unescape(text, 1))
        node.source, node.line = self.state_machine.get_source_and_line(self.lineno)
        return [node]


directives.register_directive("jinja", JinjaDirective)


class TargetDirective(JinjaDirective):
    CONTENT_TYPE = "target"
    required_arguments = 1
    has_content = False

    def run(self):  # type: ignore
        text = f'<div class="header_target" id="{self.arguments[0]}"></div>'
        node = jinjalit(text, docutils.utils.unescape(text, 1))
        node.source, node.line = self.state_machine.get_source_and_line(self.lineno)
        return [node]


directives.register_directive("target", TargetDirective)


RST_SETTINGS = {
    "input_encoding": "utf-8",
    "syntax_highlight": "short",
    "embed_stylesheet": False,
    #    'doctitle_xform': False,
    #    'initial_header_level': 1,
}


class DocTitleOnly(frontmatter.DocTitle):  # type: ignore
    def promote_subtitle(self, node):  # type: ignore
        return None


class Reader(standalone.Reader):  # type: ignore
    def get_transforms(self):  # type: ignore
        transforms = standalone.Reader.get_transforms(self)
        # We have PEP-specific frontmatter handling.
        transforms.remove(frontmatter.DocTitle)
        transforms.extend([DocTitleOnly])
        return transforms


class HTMLTranslator(docutils.writers.html5_polyglot.HTMLTranslator):  # type: ignore
    docutils.writers.html5_polyglot.HTMLTranslator.special_characters[
        ord("{")
    ] = "&#123;"
    docutils.writers.html5_polyglot.HTMLTranslator.special_characters[
        ord("}")
    ] = "&#125;"

    def __init__(self, document):  # type: ignore
        super().__init__(document)

    def visit_comment(self, node, sub=re.compile("-(?=-)").sub):  # type: ignore
        """Escape double-dashes in comment text."""
        s = "<!-- %s -->\n" % sub("- ", node.astext())

        # escape jinja tag also
        s = s.replace("{", "&#123;")
        s = s.replace("}", "&#125;")

        self.body.append(s)
        # Content already processed:
        raise docutils.nodes.SkipNode

    def visit_jinjalit(self, node):  # type: ignore
        self.body.append(node.astext())
        # Keep non-HTML raw text out of output:
        raise docutils.nodes.SkipNode

    def depart_jinjalit(self, node):  # type: ignore
        pass


def _make_pub(source_class):  # type: ignore
    pub = docutils.core.Publisher(
        reader=Reader(),
        source_class=source_class,
        destination_class=docutils.io.StringOutput,
    )

    pub.set_components("standalone", "restructuredtext", "html5")

    settings = RST_SETTINGS.copy()

    pub.process_programmatic_settings(None, settings, None)
    pub.writer.translator_class = HTMLTranslator

    return pub


def _parse(pub: Any) -> Tuple[Dict[str, Any], str]:
    pub.publish(enable_exit_status=True)

    parts = pub.writer.parts
    title = parts.get("title")
    if title:
        title = BeautifulSoup(html.unescape(title), "html.parser").text

    metadata = {"type": "article", "title": title, "has_jinja": True}

    if hasattr(pub.document, "article_metadata"):
        metadata.update(pub.document.article_metadata)

    if not metadata["title"]:
        for node in pub.document.traverse(docutils.nodes.title):
            title = node.astext()
            metadata["title"] = title
            break

    return metadata, parts.get("body")


def _load_string(string: str) -> Tuple[Dict[str, Any], str]:
    pub = _make_pub(docutils.io.StringInput)  # type: ignore
    pub.set_source(source=string)
    return _parse(pub)


def _load_file(filename: str) -> Tuple[Dict[str, Any], str]:
    pub = _make_pub(docutils.io.FileInput)  # type: ignore
    pub.set_source(source_path=os.fspath(filename))
    return _parse(pub)


def load(src: ContentSrc) -> List[Tuple[ContentSrc, str]]:
    if src.package:
        s = src.read_text()
        metadata, body = _load_string(s)
    else:
        assert src.srcpath
        metadata, body = _load_file(src.srcpath)

    src.metadata.update(metadata)
    return [(src, body)]
