# -*- encoding: utf-8 -*-
import logging

from strephit.commons.pos_tag import TTPosTagger

logger = logging.getLogger(__name__)


class SortedSet:
    """ Very simple sorted unique collection which remembers
        the order of insertion of its items
    """

    def __init__(self):
        self.items = {}

    def put(self, item):
        self.items[item] = self.items.get(item, len(self.items))
        return self.items[item]

    def index(self, item):
        return self.items.get(item, -1)


class FactExtractorFeatureExtractor:
    """ Feature extractor inspired from the fact-extractor
    """

    def __init__(self, language, window_width=2):
        self.tagger = TTPosTagger(language)
        self.feature_index = SortedSet()
        self.window_width = window_width

    def sentence_to_tokens(self, sentence_data):
        """ Transforms a sentence into a list of tokens
            :param sentence_data: Sentence data, i.e. text, frame and FEs
            :return: List of tokens
        """

        tagged = self.tagger.tag_one(sentence_data['sentence'], skip_unknown=False)

        # find entities and group them into single tokens,
        for fe, chunk in sentence_data['fes'].iteritems():
            if chunk is None:
                continue

            fe_tokens = self.tagger.tokenize(chunk)

            # find fe_tokens into tagged
            found = False
            i = j = 0
            while i < len(tagged):
                if fe_tokens[j].lower() == tagged[i][0].lower():
                    j += 1
                    if j == len(fe_tokens):
                        found = True
                        break
                else:
                    j = 0
                i += 1

            if found:
                position = i - len(fe_tokens) + 1
                pos = 'ENT' if len(fe_tokens) > 1 else tagged[position][1]
                tagged = tagged[:position] + [[chunk, pos, chunk]] + tagged[position + len(fe_tokens):]
            else:
                logger.warn('cunk "%s" of fe "%s" not found in sentence "%s"',
                            chunk, fe, sentence_data['sentence'])

        return tagged

    def feature_for(self, term, type_, position):
        """ Returns the feature for the given token, i.e. the column of the feature in a sparse matrix
            :param term: Actual term
            :param type_: Type of the term, for example token, pos or lemma
            :param position: Relative position (used for context windows)
            :return: Column of the corresponding feature
        """
        feat = '%s_%s_%+d' % (term.lower(), type_.lower(), position)
        return self.feature_index.put(feat)

    def token_to_features(self, tokens, position):
        """ Extracts the features for the token in the given position
            :param tokens: POS-tagged tokens of the sentence
            :param position: position of the token for which features are requestsd
            :return: sparse set of features (i.e. numbers are indexes in a row of a sparse matrix)
        """
        features = set()

        for i in xrange(max(position - self.window_width, 0), min(position + self.window_width + 1, len(tokens))):
            rel = i - position
            features.add(self.feature_for(tokens[i][0], 'TERM', rel))
            features.add(self.feature_for(tokens[i][1], 'POS', rel))
            features.add(self.feature_for(tokens[i][2], 'LEMMA', rel))

        return features

    def extract_features(self, sentence_data):
        """ Extracts the features for each token of the sentence
            :param sentence_data: Data of the sentence, i.e. text and FEs
            :return: List of features, each one as a sparse row
            (i.e. with the indexes of the relevant columns)
        """
        tagged = self.sentence_to_tokens(sentence_data)
        features = []

        for i in xrange(len(tagged)):
            feat = self.token_to_features(tagged, i)
            features.append(feat)

        return features
