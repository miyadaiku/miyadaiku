# -*- coding: utf-8 -*-

# type: ignore

"""
    The Pygments reStructuredText directive
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This fragment is a Docutils_ 0.5 directive that renders source code
    (to HTML only, currently) via Pygments.

    To use it, adjust the options below and copy the code into a module
    that you import on initialization.  The code then automatically
    registers a ``sourcecode`` directive that you can use instead of
    normal code blocks like this::

        .. sourcecode:: python

            My code goes here.

    If you want to have different code styles, e.g. one with line numbers
    and one without, add formatters with their names in the VARIANTS dict
    below.  You can invoke them instead of the DEFAULT one by using a
    directive option::

        .. sourcecode:: python
            :linenos:

            My code goes here.

    Look at the `directive documentation`_ to get all the gory details.

    .. _Docutils: http://docutils.sf.net/
    .. _directive documentation:
       http://docutils.sourceforge.net/docs/howto/rst-directives.html

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

# Options
# ~~~~~~~


import logging

import pygments.formatters.html
from docutils import nodes
from docutils.parsers.rst import Directive, directives
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name

logger = logging.getLogger(__name__)


# Set to True if you want inline CSS styles instead of classes
INLINESTYLES = False

# The default formatter
# DEFAULT = HtmlFormatter(noclasses=INLINESTYLES)

pygments.formatters.html._escape_html_table[ord("{")] = "&#123;"
pygments.formatters.html._escape_html_table[ord("}")] = "&#125;"


# Add name -> formatter pairs for every variant you want to use
VARIANTS = {
    "linenos": HtmlFormatter(noclasses=INLINESTYLES, linenos=True),
}

TEMPL = """
<div class="code-block">
{caption}
{parsed}
</div>
"""


class Pygments(Directive):
    """Source code syntax hightlighting."""

    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        "linenos": directives.flag,
        "caption": directives.unchanged,
    }
    has_content = True

    def run(self):
        self.assert_has_content()
        lexer = None

        if self.arguments:
            try:
                lexer = get_lexer_by_name(self.arguments[0])
            except ValueError:
                # no lexer found - use the text one instead of an exception
                logger.warn(f"no lexer for alias {self.arguments[0]!r} found")

        if not lexer:
            lexer = TextLexer()

        # take an arbitrary option if more than one is given
        linenos = "linenos" in self.options
        formatter = HtmlFormatter(noclasses=INLINESTYLES, linenos=linenos)

        parsed = highlight("\n".join(self.content), lexer, formatter)
        caption = self.options.get("caption", "")
        caption = pygments.formatters.html.escape_html(caption)
        if caption:
            caption = f"""<div class="code-block-caption">{caption}</div>"""
        parsed = TEMPL.format(parsed=parsed, caption=caption)
        return [nodes.raw("", parsed, format="html")]


directives.register_directive("code-block", Pygments)
