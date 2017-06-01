import os
import datetime
import dateutil.parser
import collections
import docutils
import docutils.core
import docutils.nodes
import docutils.writers.html5_polyglot
import docutils.utils
from docutils.writers.html5_polyglot import HTMLTranslator
from docutils.parsers.rst import Directive, directives, roles
from docutils.parsers.rst.states import MarkupError, Body

import pygments.formatters.html
from . import pygment_directive

pygments.formatters.html._escape_html_table[ord(
        '{')] = '&#123;'
pygments.formatters.html._escape_html_table[ord(
        '}')] = '&#125;'

class Metadata:
    def type_str(v):
        return v.strip()
    title = category = template = filename = type_str
    template2 = type_str

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

def format_metadata(d):
    ret = {}
    for k, v in d.items():
        f = getattr(Metadata, k, None)
        if f:
            v = f(v)
        ret[k] = v
    return ret


class _RstDirective(Directive):
    def run(self):
        try:
            options = format_metadata(self.options)
        except Exception as e:
            raise MarkupError(str(e))

        options['type'] = self.CONTENT_TYPE

        cur = getattr(self.state.document, "article_metadata", {})
        cur.update(options)
        self.state.document.article_metadata = cur
        return []


class ArticleDirective(_RstDirective):
    CONTENT_TYPE = 'article'

    required_arguments = 0
    optional_arguments = 0

    # use defaultdict to pass undefined arguments.
    option_spec = collections.defaultdict(lambda :directives.unchanged,
                  {'title': directives.unchanged,
                   'draft': directives.unchanged,
                   'date': directives.unchanged,
                   'category': directives.unchanged,
                   'tags': directives.unchanged,
                   'template': directives.unchanged,
                   'filename': directives.unchanged,})


directives.register_directive('article', ArticleDirective)


class SnippetDirective(_RstDirective):
    CONTENT_TYPE = 'snippet'
    required_arguments = 0
    optional_arguments = 0
    option_spec = {'title': directives.unchanged}


directives.register_directive('snippet', SnippetDirective)


class jinjalit(docutils.nodes.Inline, docutils.nodes.TextElement):
    pass


def jinja_role(role, rawtext, text, lineno, inliner, options={}, content=[]):
    node = jinjalit(rawtext, docutils.utils.unescape(text, 1), **options)
    node.source, node.line = inliner.reporter.get_source_and_line(lineno)
    return [node], []


roles.register_local_role('jinja', jinja_role)


settings = {
    'input_encoding': 'utf-8',
    'syntax_highlight': 'short',
    'embed_stylesheet': False,
#    'doctitle_xform': False
}


class HTMLTranslator(docutils.writers.html5_polyglot.HTMLTranslator):
    docutils.writers.html5_polyglot.HTMLTranslator.special_characters[ord(
        '{')] = '&#123;'
    docutils.writers.html5_polyglot.HTMLTranslator.special_characters[ord(
        '}')] = '&#125;'

    def visit_jinjalit(self, node):
        self.body.append(node.astext())
        # Keep non-HTML raw text out of output:
        raise docutils.nodes.SkipNode

    def depart_jinjalit(self, node):
        pass


def load(path):
    pub = docutils.core.Publisher(
        source_class=docutils.io.FileInput,
        destination_class=docutils.io.StringOutput)

    pub.set_components("standalone", "restructuredtext", "html5")
    pub.process_programmatic_settings(None, settings, None)
    pub.set_source(source_path=os.fspath(path))
    pub.writer.translator_class = HTMLTranslator

    pub.parser.state_classes


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
