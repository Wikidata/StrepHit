# -*- encoding: utf-8 -*-
import json
import logging
import itertools
from inspect import isclass
from collections import Counter

import click
from sklearn.externals import joblib
from sklearn.svm import LinearSVC, SVC
from sklearn.grid_search import GridSearchCV
from sklearn import metrics
from sklearn.neighbors import KNeighborsClassifier
from sklearn.dummy import DummyClassifier

from sklearn.ensemble import RandomForestClassifier

from strephit.classification.classifiers import FeatureSelectedClassifier
from strephit.commons.classification import reverse_gazetteer
from strephit.classification.feature_extractors import BagOfTermsFeatureExtractor, Word2VecFeatureExtractor

logger = logging.getLogger(__name__)


class MultimodelGridSearchCV:
    """ Cross-validated grid search supporting multiple models
        (each one with its own parameter space)

        Uses `sklearn.grid_search.GridSearchCV` under the hood
    """

    def __init__(self, *models, **kwargs):
        """ Initializes the grid search

            :param list models: List of models to use. Each one should be a tuple
             with a model instance or class and a dictionary for the search space.
            :param kwargs: addition initialization arguments
             for `sklearn.grid_search.GridSearchCV`
        """
        self.models = filter(None, models)
        kwargs['refit'] = True
        self.kwargs = kwargs

    def fit(self, training_sets):
        """ Searches for the best estimator and its arguments as well as the best
            training set amongst those specified.

            :param generator training_sets: Training set to use. Should be a sequence
             of tuples (x, y, metadata) where x is the training set, y is the
             correct answer for each chunk and metadata contains additional data that will
             be returned back
            :return: the metadata of the training set which yielded the best score,
             the best score obtained by the model, parameters of the model and
             fitted model itself
            :rtype: tuple
        """
        best_training, best_score, best_params, best_model = None, None, None, None
        for i, (metadata, extractor) in enumerate(training_sets):
            for model, grid in self.models:
                assert isclass(model)

                x, y = extractor.get_features(refit=True)

                grid['model_cls'] = [model]
                grid['selector_column'] = [None, extractor.lu_column()]

                search = GridSearchCV(
                    FeatureSelectedClassifier(model), param_grid=grid, **self.kwargs
                )
                search.fit(x, y)

                score, params, model = search.best_score_, search.best_params_, search.best_estimator_
                logger.debug('%s with parameters %s and training meta %s has score %s',
                             type(model), params, metadata, score)
                if best_score is None or score > best_score:
                    best_training, best_score, best_params, best_model = (x, y, metadata), score, params, model

        return best_training, best_score, best_params, best_model


# needs to be pickleable and callable
class Scorer(object):
    def __init__(self, scoring, skip_majority):
        self.scoring = scoring
        self.skip_majority = skip_majority

    def __call__(self, estimator, x, y_true):
        y_pred = estimator.predict(x)

        if self.skip_majority:
            most_frequent = Counter(y_true).most_common(1)[0][0]
            labels = set(y_true) | set(y_pred)
            labels.discard(most_frequent)
            labels = list(labels)
        else:
            labels = list(set(y_true) | set(y_pred))

        return metrics.f1_score(y_true, y_pred, labels=labels, average=self.scoring)


def get_training_sets(training_set, language, gazetteer, word2vec_model, independent_lus):
    extractor_args = itertools.chain(
        itertools.product([BagOfTermsFeatureExtractor], [True, False], [0, 1, 2], [None, 100, 1000]),

        itertools.product([Word2VecFeatureExtractor], [word2vec_model], [True, False], [0, 1, 2])
        if word2vec_model else []
    )

    lus = set(json.loads(row)['lu'] for row in training_set) if independent_lus else ['$all']

    count = 0
    for gaz in list(gazetteer) + [None]:
        for args in extractor_args:
            for lu in lus:
                logger.debug('%d) gazetteer: %s, extractor params: %s, lu: %s',
                             count, gaz.name if gaz else None, args, lu)
                count += 1

                extractor, init_args = args[0], args[1:]
                extractor = extractor(language, *init_args)
                gazetteer = reverse_gazetteer(json.load(gazetteer)) if gaz else {}

                training_set.seek(0)
                for row in training_set:
                    data = json.loads(row)
                    if not independent_lus or data['lu'] in lus:
                        extractor.process_sentence(data['sentence'], data['lu'], data['fes'],
                                                   add_unknown=True, gazetteer=gazetteer)

                meta = {
                    'lu': lu,
                    'gazetteer': gaz,
                    'extractor_cls': args[0],
                    'extractor_args': [language] + list(args[1:]),
                    #'extractor': extractor
                }

                yield meta, extractor


def get_models(test):
    return [
        (LinearSVC, {
            'C': [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0],
            'multi_class': ['ovr', 'crammer_singer'],
        }),
    ] + ([
        (KNeighborsClassifier, {
            'weights': ['uniform', 'distance'],
        }),
        (SVC, {
            'C': [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0],
            'kernel': ['linear', 'poly', 'rbf', 'sigmoid'],
            'decision_function_shape': ['ovr', 'ovo'],
        }),
        (RandomForestClassifier, {
            'criterion': ['gini', 'entropy'],
            'min_samples_split': [5, 10, 25],
            'min_samples_leaf': [5, 10, 25],
            'n_estimators': [5, 10, 50, 100],
        })
    ] if not test else [])


@click.command()
@click.argument('training-set', type=click.File('r'))
@click.argument('language')
@click.option('--gold-standard', type=click.File('r'))
@click.option('--gazetteer', type=click.File('r'), multiple=True)
@click.option('--n-folds', default=10)
@click.option('--n-jobs', default=1)
@click.option('--scoring', default='macro')
@click.option('--output', type=click.Path(dir_okay=False, writable=True),
              default='output/classifier_model.pkl', help='Where to save the model')
@click.option('--test', is_flag=True, help='Only try a small subset of the models')
@click.option('--word2vec-model', type=click.Path(exists=True, dir_okay=False),
              help='google for GoogleNews-vectors-negative300.bin.gz')
@click.option('--independent-lus', is_flag=True,
              help='Perform model selection over each LU (returns only the best one overall)')
def main(training_set, language, gold_standard, gazetteer, n_folds, n_jobs,
         scoring, output, test, word2vec_model, independent_lus):
    """ Searches for the best hyperparameters """

    logger.info('Searching for the best model and parameters')

    training_sets = get_training_sets(training_set, language, gazetteer, word2vec_model, independent_lus)
    models = get_models(test)

    search = MultimodelGridSearchCV(*models, cv=n_folds, n_jobs=n_jobs,
                                    scoring=Scorer(scoring, True))
    (x_tr, y_tr, best_training_meta), best_score, best_params, best_model = search.fit(training_sets)

    logger.info('Evaluation Results')
    logger.info('  Best model: %s', best_model.__class__.__name__)
    logger.info('  Score: %f', best_score)
    logger.info('  Parameters: %s', best_params)
    logger.info('  Gazetteer: %s', best_training_meta['gazetteer'])
    logger.info('  Extractor: %s', best_training_meta['extractor_cls'].__name__)
    logger.info('  Extractor args: %s', best_training_meta['extractor_args'])

    joblib.dump((best_model, best_training_meta), output)
    logger.info("Done, dumped model to '%s'", output)

    if not gold_standard:
        logger.info('Skipping gold standard evaluation')
        return

    logger.info('Evaluating on the gold standard')

    extractor = best_training_meta['extractor']
    gazetteer = best_training_meta['gazetteer']

    extractor.start()
    for row in gold_standard:
        data = json.loads(row)
        extractor.process_sentence(data['sentence'], data['lu'], data['fes'],
                                   add_unknown=False, gazetteer=gazetteer)
    x_gold, y_gold = extractor.get_features(refit=False)

    dummy = DummyClassifier(strategy='stratified')
    dummy.fit(x_tr, y_tr)

    logger.info('Dummy model has a weighted-averaged F1 on the gold standard of %.4f',
                Scorer(scoring, True)(dummy, x_gold, y_gold))

    logger.info('Best model has a weighted-averaged F1 on the gold standard of %.4f',
                Scorer(scoring, True)(best_model, x_gold, y_gold))
