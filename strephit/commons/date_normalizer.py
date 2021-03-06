from __future__ import absolute_import

import yaml
import re
import os
import logging

logger = logging.getLogger(__name__)


class DateNormalizer(object):
    """
    find matches in text strings using regular expressions and transforms them
    according to a pattern transformation expression evaluated on the match

    the specifications are given in yaml format and allow to define meta functions
    and meta variables as well as the pattern and transformation rules themselves.

    meta variables will be placed inside patterns which use them in order to
    make writing patterns easier. meta variables will be available to use from
    inside the meta functions too as a dictionary named meta_vars

    a pattern transformation expression is an expression which will be evaluated
    if the corresponding regular expression matches. the pattern transformation
    will have access to all the meta functions and meta variables defined and
    to a variable named 'match' containing the regex match found
    """

    def __init__(self, language=None, specs=None):
        assert language or specs, 'please specify either one of the pre-set ' \
                                  'languages or provide a custom rule set'
        if specs is None:
            path = os.path.join(os.path.dirname(__file__), 'resources',
                                'normalization_rules_%s.yml' % language)

            with open(path) as f:
                specs = yaml.load(f)

        self._meta_init(specs)
        basic_r = {name: pattern for name, pattern in self.meta_vars.iteritems()}

        self.regexes = {}
        for category, regexes in specs.iteritems():
            regexes = sum((x.items() for x in regexes), [])
            self.regexes[category] = [(re.compile(pattern.format(**basic_r)
                                                         .replace(' ', '\\s*'),
                                                  re.IGNORECASE), result)
                                      for pattern, result in regexes]

    def _meta_init(self, specs):
        """ Reads the meta variables and the meta functions from the specification

        :param dict specs: The specifications loaded from the file
        :return: None
        """
        # read meta variables and perform substitutions
        self.meta_vars = {}
        if '__meta_vars__' in specs:
            for definition in specs.pop('__meta_vars__'):
                var, value = definition.items()[0]
                if isinstance(value, basestring):
                    self.meta_vars[var] = value.format(**self.meta_vars)
                elif isinstance(value, dict):
                    self.meta_vars[var] = {
                        k: v.format(**self.meta_vars) for k, v in value.iteritems()
                    }

        # compile meta functions in a dictionary
        self.meta_funcs = {}
        if '__meta_funcs__' in specs:
            for f in specs.pop('__meta_funcs__'):
                exec f in self.meta_funcs

            # make meta variables available to the meta functions just defined
            self.meta_funcs['__builtins__']['meta_vars'] = self.meta_vars

        self.globals = self.meta_funcs
        self.globals.update(self.meta_vars)

    def normalize_one(self, expression, conflict='longest'):
        """ Find the matching part in the given expression

        :param str expression: The expression in which to search the match
        :param str conflict: Whether to return the first match found or scan
         through all the provided regular expressions and return the longest
         or shortest part of the string matched by a regular expression.
         Note that the match will always be the first one found in the string,
         this parameter tells how to resolve conflicts when there is more than
         one regular expression that returns a match. When more matches have
         the same length the first one found counts
         Allowed values are `first`, `longest` and `shortest`
        :return: Tuple with (start, end), category, result
        :rtype: tuple

        Sample usage:

        >>> from strephit.commons.date_normalizer import DateNormalizer
        >>> DateNormalizer('en').normalize_one('Today is the 1st of June, 2016')
        ((13, 30), 'Time', {'month': 6, 'day': 1, 'year': 2016})
        """

        best_match = None
        expression = expression.lower()
        for category, regexes in self.regexes.iteritems():
            for regex, transform in regexes:
                match = regex.search(expression)
                if not match:
                    continue
                elif conflict == 'first':
                    return self._process_match(category, transform, match, 0)
                elif best_match is None or \
                        conflict == 'longest' and match.end() - match.start() > best_match[1] or \
                        conflict == 'shortest' and match.end() - match.start() < best_match[1]:
                    best_match = match, match.end() - match.start(), category, transform

        if best_match is None:
            return (-1, -1), None, None
        else:
            match, _, category, transform = best_match
            return self._process_match(category, transform, match, 0)

    def normalize_many(self, expression):
        """ Find all the matching entities in the given expression expression

        :param str expression: The expression in which to look for
        :return: Generator of tuples (start, end), category, result


        Sample usage:

        >>> from pprint import pprint
        >>> from strephit.commons.date_normalizer import DateNormalizer
        >>> pprint(list(DateNormalizer('en').normalize_many('I was born on April 18th, '
        ...                                                 'and today is April 18th, 2016!')))
        [((14, 24), 'Time', {'day': 18, 'month': 4}),
         ((39, 55), 'Time', {'day': 18, 'month': 4, 'year': 2016})]

        """

        # start matching from here, and move forward as new matches
        # are found so to avoid overlapping matches and return
        # the correct offset inside the original sentence
        position = 0
        expression = expression.lower()

        for category, regexes in self.regexes.iteritems():
            for regex, transform in regexes:
                end = 0
                for match in regex.finditer(expression[position:]):
                    yield self._process_match(category, transform, match, position)
                    end = max(end, match.end())
                position += end

    def _process_match(self, category, transform, match, first_position):
        result = eval(transform, self.globals, {'match': match})
        start, end = match.span()
        return (first_position + start, first_position + end), category, result


NORMALIZERS = {}

def normalize_numerical_fes(language, text):
    """ Normalize numerical FEs in a sentence
    """
    if language not in NORMALIZERS:
        NORMALIZERS[language] = DateNormalizer(language)
    normalizer = NORMALIZERS[language]

    logger.debug('labeling and normalizing numerical FEs of language %s...', language)
    count = 0
    for (start, end), tag, norm in normalizer.normalize_many(text):
        chunk = text[start:end]
        logger.debug('Chunk [%s] normalized into [%s], tagged as [%s]' % (chunk, norm, tag))
        # All numerical FEs are extra ones and their values are literals
        fe = {
            'fe': tag,
            'chunk': chunk,
            'type': 'extra',
            'literal': norm,
            'score': 1.0
        }
        count += 1
        yield fe
    logger.debug('found %d numerical FEs into "%s"', count, text)
