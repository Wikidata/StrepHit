# -*- encoding: utf-8 -*-
import logging

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.decomposition import TruncatedSVD
import gensim
from strephit.commons.pos_tag import TTPosTagger
from strephit.commons.stopwords import StopWords


logger = logging.getLogger(__name__)


class BagOfTermsFeatureExtractor(object):
    """ Extracts features from sentences. Will process sentences one by one
        accumulating their features and finalizes them into the final
        training set.

        It should be used to extract features prior to classification,
        in which case the fe arguments can be used to group tokens of
        the same entity into a single chunk while ignoring the actual
        frame element name, e.g. `fes = dict(enumerate(entities))`
    """

    def __init__(self, language='en', window_width=2, collapse_fes=True, target_size=None):
        """ Initializes the extractor.

            :param language: The language of the sentences that will be used
            :param window_width: how many tokens to look before and after a each
             token when building its features.
            :param collapse_fes: Whether to collapse FEs to a single token
             or to keep them split.
        """
        self.language = language
        self.tagger = TTPosTagger(language)
        self.window_width = window_width
        self.collapse_fes = collapse_fes
        self.unk_feature = 'UNK'
        self.vectorizer = DictVectorizer()
        self.target_size = target_size
        self.reducer = TruncatedSVD(target_size) if target_size else None
        self.vocabulary = set()
        self.label_index = {}
        self.lu_index = {}
        self.stopwords = set(w.lower() for w in StopWords().words(language))
        self.start()

    def start(self):
        """ Clears the samples accumulated so far and starts over.
        """
        self.samples = []

    def lu_column(self):
        return self.vectorizer.vocabulary_['lu'] if not self.target_size else None

    def process_sentence(self, sentence, lu, fes, add_unknown, gazetteer):
        """ Extracts and accumulates features for the given sentence

            :param unicode sentence: Text of the sentence
            :param unicode lu: lexical unit of the sentence
            :param dict fes: Dictionary with FEs and corresponding chunks
            :param bol add_unknown: Whether unknown tokens should be added
             to the index of treaded as a special, unknown token.
             Set to True when building the training set and to False
             when building the features used to classify new sentences
            :param dict gazetteer: Additional features to add when a given
             chunk is found in the sentence. Keys should be chunks and
             values should be list of features
            :return: List of tuples whose first elements are chunks of words
             and the second ones indicate whether the chunk was used as a
             sample or skipped altogether
            :type: list of tuples (chunk, is_sample)
        """

        gazetteer = gazetteer or {}
        tagged = self.sentence_to_tokens(sentence, fes)

        ret = []
        for position in xrange(len(tagged)):
            if tagged[position][0].lower() in self.stopwords:
                ret.append((tagged[position][0], False))
                continue
            else:
                ret.append((tagged[position][0], True))

            # add the unknown feature to every sample to trick the dict vectorizer into
            # thinking that there is a feature like that. will be useful when add_unknown
            # is false, because by default the dict vectorizer skips unseen labels
            self.lu_index[lu] = self.lu_index.get(lu, len(self.lu_index))
            sample = {'unk': self.unk_feature, 'lu': self.lu_index[lu]}

            for i in xrange(max(position - self.window_width, 0),
                            min(position + self.window_width + 1, len(tagged))):
                if tagged[i][0].lower() in self.stopwords:
                    continue

                rel = i - position

                self.add_feature_to(sample, 'TERM%+d' % rel, tagged[i][0], add_unknown)
                self.add_feature_to(sample, 'POS%+d' % rel, tagged[i][1], add_unknown)
                self.add_feature_to(sample, 'LEMMA%+d' % rel, tagged[i][2], add_unknown)

                for feat in gazetteer.get(tagged[i][0], []):
                    sample['GAZ%+d' % rel] = feat

            label = 'O' if len(tagged[i]) == 3 else tagged[i][3]
            self.label_index[label] = self.label_index.get(label, len(self.label_index))
            self.samples.append((sample, label))

        return ret

    def add_feature_to(self, sample, feature_name, feature_value, add_unknown):
        if add_unknown or feature_value in self.vocabulary:
            sample[feature_name] = feature_value
            self.vocabulary.add(feature_value)
        else:
            sample[feature_name] = self.unk_feature

    def get_features(self, refit):
        """ Returns the final features matrix

            :param bool refit: whether to refit the features or use the previous model.
             use refit=True when training and refit=False when retrieving features
             for classifying unknown samples
            :return: A matrix whose rows are samples and columns are features and a
             row vector with the sample label (i.e. the correct answer for the classifier)
            :rtype: tuple
        """
        samples, labels = zip(*self.samples)

        if refit:
            features = self.vectorizer.fit_transform(samples)
            if self.target_size:
                features = self.reducer.fit_transform(features)
        else:
            features = self.vectorizer.transform(samples)
            if self.target_size:
                features = self.reducer.transform(features)

        labels = np.array([self.label_index[label] for label in labels])

        return features, labels

    def sentence_to_tokens(self, sentence, fes):
        """ Transforms a sentence into a list of tokens. Appends the FE type
            to all tokens composing a certain FE and optionally group them into
            a single token.

            :param unicode sentence: Text of the sentence
            :param dict fes: mapping FE -> chunk
            :return: List of tokens
        """

        if not sentence.strip():
            return []

        tagged = self.tagger.tag_one(sentence, skip_unknown=False)

        tokens = []
        for fe, chunk in fes.iteritems():
            if chunk is None:
                continue

            fe_tokens = self.tagger.tokenize(chunk)
            if not fe_tokens:
                continue

            # find fe_tokens into tagged
            found = False
            i = j = 0
            while i < len(tagged):
                if len(tagged[i]) == 3 and fe_tokens[j].lower() == tagged[i][0].lower():
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

                if self.collapse_fes:
                    # make a single token with the whole chunk
                    tokens.append([chunk, pos, chunk, fe])
                    tagged = tagged[:position] + [[chunk, pos, chunk, fe]] + tagged[position + len(fe_tokens):]
                else:
                    # set custom lemma and label for the tokens of the FE
                    for i in xrange(position, position + len(fe_tokens)):
                        token, pos, _ = tagged[i]
                        token = (token, pos, 'ENT', fe)
                        tagged[i] = token
                        tokens.append(token)
            else:
                logger.debug('cunk "%s" of fe "%s" not found in sentence "%s". Overlapping chunks?',
                             chunk, fe, sentence)

        return tokens

    def __getstate__(self):
        return (self.language, self.unk_feature, self.window_width, self.samples,
                self.vocabulary, self.label_index, self.vectorizer, self.collapse_fes,
                self.reducer, self.target_size)

    def __setstate__(self, (language, unk_feature, window_width, samples, vocabulary,
                     label_index, vectorizer, collapse_fes, reducer, target_size)):
        self.__init__(language, window_width, collapse_fes, target_size)
        self.samples = samples
        self.vocabulary = vocabulary
        self.unk_feature = unk_feature
        self.label_index = label_index
        self.vectorizer = vectorizer
        self.reducer = reducer

    def __str__(self):
        return '%s(window_width=%d, collapse_fes=%r)' % (
            self.__class__.__name__, self.window_width, self.collapse_fes
        )


class Word2VecFeatureExtractor(BagOfTermsFeatureExtractor):
    """ Extracts features using word2vec's cbow pre-trained model as
        toknens' features with a fallback on a bag-of-terms approach
        for tokens outside the vocabulary
    """
    def __init__(self, language, model_path, window_width=2, collapse_fes=True):
        super(Word2VecFeatureExtractor, self).__init__(language, window_width, collapse_fes)
        self.cbow = gensim.models.Word2Vec.load_word2vec_format(model_path, binary=True)

    def add_feature_to(self, sample, feature_name, feature_value, add_unknown):
        if add_unknown or feature_value in self.vocabulary:
            if feature_name.startswith('TERM') and feature_value in self.cbow:
                sample['W2V'] = 1
                for i, x in enumerate(self.cbow[feature_value]):
                    sample['%s-W2V-%d' % (feature_name, i)] = x
            else:
                sample['W2V'] = 0
                sample[feature_name] = feature_value
                self.vocabulary.add(feature_value)
        else:
            sample['W2V'] = 0
            sample[feature_name] = self.unk_feature
