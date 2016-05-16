# -*- encoding: utf-8 -*-
import logging
import numpy as np
from scipy.sparse import csr_matrix
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


class BaseFeatureExtractor:
    """ Feature extractor template. Will process sentences one by one
        accumulating their features and finalizes them into the final
        training set.
    """

    def process_sentence(self, sentence, fes):
        """ Extracts and accumulates features for the given sentence
            :param sentence: Text of the sentence
            :param fes: Dictionary with FEs and corresponding chunks
            :return: Nothing
        """
        raise NotImplemented

    def get_training_set(self):
        """ Returns the final training set
            :return: A matrix whose rows are samples and columns are features and a
            column vector with the sample label (i.e. the correct answer for the classifier)
            :rtype: tuple
        """
        raise NotImplemented


class FactExtractorFeatureExtractor(BaseFeatureExtractor):
    """ Feature extractor inspired from the fact-extractor
    """

    def __init__(self, language, window_width=2):
        self.tagger = TTPosTagger(language)
        self.feature_index = SortedSet()
        self.role_index = SortedSet()
        self.window_width = window_width
        self.features = []

    def sentence_to_tokens(self, sentence, fes):
        """ Transforms a sentence into a list of tokens
            :param sentence: Text of the sentence
            :param fes: mapping FE -> chunk
            :return: List of tokens
        """

        tagged = self.tagger.tag_one(sentence, skip_unknown=False)

        # find entities and group them into single tokens,
        for fe, chunk in fes.iteritems():
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
                tagged = tagged[:position] + [[chunk, pos, chunk, fe]] + tagged[position + len(fe_tokens):]
            else:
                logger.warn('cunk "%s" of fe "%s" not found in sentence "%s"',
                            chunk, fe, sentence)

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

    def extract_features(self, sentence, fes):
        """ Extracts the features for each token of the sentence
            :param sentence: Text of the sentence
            :param fes: mapping FE -> chunk
            :return: List of features, each one as a sparse row
             (i.e. with the indexes of the relevant columns)
        """
        tagged = self.sentence_to_tokens(sentence, fes)
        features = []

        for i in xrange(len(tagged)):
            feat = self.token_to_features(tagged, i)
            label = 'O' if len(tagged[i]) == 3 else tagged[i][3]

            features.append((feat, self.role_index.put(label)))

        return features

    def process_sentence(self, sentence, fes):
        self.features.extend(self.extract_features(sentence, fes))

    def get_training_set(self):
        X, Y = [], []
        data, indices, indptr = [], [], []

        for sample, label in self.features:
            Y.append(label)

            indptr.append(len(data))
            for feature in sample:
                indices.append(int(feature))
                data.append(1.0)

        indptr.append(len(data))
        X = csr_matrix((data, indices, indptr),
                       shape=(len(indptr) - 1, len(self.feature_index.items)),
                       dtype=np.float32)
        Y = np.array(Y)

        return X, Y