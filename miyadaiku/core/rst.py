import re
import os
import datetime
import dateutil.parser
import collections
import docutils
import docutils.core
import docutils.nodes
import docutils.writers.html5_polyglot
import docutils.utils
from docutils.parsers.rst import Directive, directives, roles
from docutils.parsers.rst.states import MarkupError, Body

from . import pygment_directive


class _RstDirective(Directive):
    def run(self):
        if 'type' not in self.options:
            self.options['type'] = self.CONTENT_TYPE

        cur = getattr(self.state.document, "article_metadata", {})
        cur.update(self.options)
        self.state.document.article_metadata = cur
        return []


class ArticleDirective(_RstDirective):
    CONTENT_TYPE = 'article'

    required_arguments = 0
    optional_arguments = 0

    # use defaultdict to pass undefined arguments.
    option_spec = collections.defaultdict(lambda: directives.unchanged,
                                          {'title': directives.unchanged,
                                           'draft': directives.unchanged,
                                           'date': directives.unchanged,
                                           'category': directives.unchanged,
                                           'tags': directives.unchanged,
                                           'template': directives.unchanged,
                                           'filename': directives.unchanged,
                                           })


directives.register_directive('article', ArticleDirective)


class SnippetDirective(_RstDirective):
    CONTENT_TYPE = 'snippet'
    required_arguments = 0
    optional_arguments = 0

    # use defaultdict to pass undefined arguments.
    option_spec = collections.defaultdict(lambda: directives.unchanged,
                                          {'title': directives.unchanged})


directives.register_directive('snippet', SnippetDirective)


class jinjalit(docutils.nodes.Inline, docutils.nodes.TextElement):
    pass


def jinja_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    node = jinjalit(rawtext, docutils.utils.unescape(text, 1), **options)
    node.source, node.line = inliner.reporter.get_source_and_line(lineno)
    return [node], []


roles.register_local_role('jinja', jinja_role)


class JinjaDirective(Directive):
    required_arguments = 0
    optional_arguments = 0
    has_content = True

    def run(self):
        text = '\n'.join(self.content)
        node = jinjalit(text, docutils.utils.unescape(text, 1))
        node.source, node.line = self.state_machine.get_source_and_line(self.lineno)
        return [node]


directives.register_directive('jinja', JinjaDirective)


settings = {
    'input_encoding': 'utf-8',
    'syntax_highlight': 'short',
    'embed_stylesheet': False,
    #    'doctitle_xform': False,
    #    'initial_header_level': 1,
}


class HTMLTranslator(docutils.writers.html5_polyglot.HTMLTranslator):
    docutils.writers.html5_polyglot.HTMLTranslator.special_characters[ord(
        '{')] = '&#123;'
    docutils.writers.html5_polyglot.HTMLTranslator.special_characters[ord(
        '}')] = '&#125;'

    def __init__(self, document):
        super().__init__(document)
#        self.initial_header_level = 2

    def visit_comment(self, node,
                      sub=re.compile('-(?=-)').sub):
        """Escape double-dashes in comment text."""
        s = '<!-- %s -->\n' % sub('- ', node.astext())

        # escape jinja tag also
        s = s.replace('{', '&#123;')
        s = s.replace('}', '&#125;')

        self.body.append(s)
        # Content already processed:
        raise docutils.nodes.SkipNode

    def visit_jinjalit(self, node):
        self.body.append(node.astext())
        # Keep non-HTML raw text out of output:
        raise docutils.nodes.SkipNode

    def depart_jinjalit(self, node):
        pass


def _make_pub(source_class):
    pub = docutils.core.Publisher(
        source_class=source_class,
        destination_class=docutils.io.StringOutput)

    pub.set_components("standalone", "restructuredtext", "html5")
    pub.process_programmatic_settings(None, settings, None)
    pub.writer.translator_class = HTMLTranslator

    return pub


def _parse(pub):
    pub.publish(enable_exit_status=True)

    parts = pub.writer.parts
    metadata = {
        'type': 'article',
        'title': parts.get("title"),
    }

    if hasattr(pub.document, "article_metadata"):
        metadata.update(pub.document.article_metadata)

    if not metadata['title']:
        for node in pub.document.traverse(docutils.nodes.title):
            title = node.astext()
            metadata['title'] = title
            break

    return metadata, parts.get('body')


def load(path):
    pub = _make_pub(docutils.io.FileInput)
    pub.set_source(source_path=os.fspath(path))
    return _parse(pub)


def load_string(string):
    pub = _make_pub(docutils.io.StringInput)
    pub.set_source(source=string)
    return _parse(pub)
