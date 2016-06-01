# -*- coding: utf-8 -*-
"""
    sphinx-wikisyntax
    ~~~~~~~~~~~~~~~~~~~~

    Wikisyntax Sphinx builder.
"""

from sphinx.builders.text import TextBuilder
from writer import WikisyntaxWriter


class WikisyntaxBuilder(TextBuilder):
    name = 'wikisyntax'
    format = 'wikisyntax'
    out_suffix = '.wiki'
    allow_parallel = True

    def prepare_writing(self, docnames):
        self.writer = WikisyntaxWriter(self)
