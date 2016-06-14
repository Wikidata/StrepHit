# -*- coding: utf-8 -*-
"""
    sphinx_wikisyntax
    ~~~~~~~~~~~~~~~~~~~

    Custom docutils writer for wikisyntax
"""
from docutils import writers, nodes
from sphinx.writers.text import TextTranslator


class WikisyntaxWriter(writers.Writer):
    supported = ('text',)
    settings_spec = ('No options here.', '', ())
    settings_defaults = {}

    output = None

    def __init__(self, builder):
        writers.Writer.__init__(self)
        self.builder = builder
        self.translator_class = self.builder.translator_class or WikisyntaxTranslator

    def translate(self):
        visitor = self.translator_class(self.document, self.builder)
        self.document.walkabout(visitor)
        self.output = visitor.body


class WikisyntaxTranslator(TextTranslator):

    MAXWIDTH = 20000000000
    STDINDENT = 1

    def depart_document(self, node):
        self.end_state()
        self.body = self.nl.join(line and (':'*indent + line)
                                 for indent, lines in self.states[0]
                                 for line in lines)

    def depart_title(self, node):
        """ Called when the end of a section's title is encountered
        """
        text = ''.join(x[1] for x in self.states.pop() if x[0] == -1)
        delimiter = '=' * self.sectionlevel
        self.stateindent.pop()

        # remove empty sections by looking at the last item inserted
        # iif it is a title with the same or deeper level of this one then it's empty
        # it's okay to show titles when they are immediately followed by a sub-title
        if len(self.states[-1]) > 0:
            last = self.states[-1][-1]
            if last[0] == 0 and last[1][0].startswith(delimiter):
                self.states[-1].pop()

        back_to_top = '\n[[#toctitle|back to top]]\n'
        self.states[-1].append((0, [' '.join([delimiter, text, delimiter, back_to_top])]))

    def visit_desc_signature(self, node):
        """ Called when the full name (incl. module) of a function is encountered
        """
        self.new_state(0)
        self.add_text('<br />')
        self.add_text("'''")

    def visit_desc_parameterlist(self, node):
        """ Called when the parameter list of a function is encountered
        """
        self.add_text("'''")
        self.add_text('(')
        self.first_param = 1

    def depart_table(self, node):
        text = []
        text.append('<table border="1">')

        text.append('<tr>')
        for field in self.table[1]:
            text.append('<th>%s</th>' % field.rstrip('\n'))
        text.append('</tr>')

        for row in self.table[3:]:
            text.append('<tr>')
            for field in row:
                text.append('<td>%s</td>' % field.rstrip('\n'))
            text.append('</tr>')
        text.append('</table>')

        self.add_text(''.join(text))
        self.table = None
        self.end_state(wrap=False)

    def visit_transition(self, node):
        self.new_state(0)
        self.add_text('----')
        self.end_state()
        raise nodes.SkipNode

    def depart_list_item(self, node):
        if self.list_counter[-1] == -1:
            self.end_state(first='* ')
        elif self.list_counter[-1] == -2:
            pass
        else:
            self.end_state(first='# ')

    def visit_centered(self, node):
        self.add_text('{center|')

    def depart_centered(self, node):
        self.add_text('}')

    def visit_block_quote(self, node):
        self.new_state()
        self.add_text('<blockquote>')

    def depart_block_quote(self, node):
        self.add_text('</blockquote>')
        self.end_state()

    def visit_emphasis(self, node):
        self.add_text("''")

    def depart_emphasis(self, node):
        self.add_text("''")

    def visit_literal_emphasis(self, node):
        self.add_text("''")

    def depart_literal_emphasis(self, node):
        self.add_text("''")

    def visit_strong(self, node):
        self.add_text("'''")

    def depart_strong(self, node):
        self.add_text("'''")

    def visit_literal_strong(self, node):
        self.add_text("'''")

    def depart_literal_strong(self, node):
        self.add_text("'''")

    def visit_subscript(self, node):
        self.add_text('<sub>')

    def depart_subscript(self, node):
        self.add_text('</sub>')

    def visit_superscript(self, node):
        self.add_text('<sup>')

    def depart_superscript(self, node):
        self.add_text('</sup>')

    def visit_doctest_block(self, node):
        self.new_state(0)

    def depart_doctest_block(self, node):
        _, doctest = self.states.pop()[0]
        self.states.append([(0, [
            '<syntaxhighlight lang="python">' + self.nl +
            doctest + self.nl +
            '</syntaxhighlight>'
        ])])

        self.end_state(wrap=False)

    def visit_target(self, node):
        _, text = self.states[-1].pop()
        url = node.rawsource[2:-1]
        self.add_text('[%s %s]' % (url, text))

    def depart_target(self, node):
        pass

    def end_state(self, wrap=False, end=[''], first=None):
        return TextTranslator.end_state(self, wrap, end, first)
