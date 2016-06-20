# -*- encoding: utf-8 -*-
import json
import logging
import itertools
from inspect import isclass

import click
from sklearn.externals import joblib
from sklearn.svm import LinearSVC, SVC

from sklearn.grid_search import GridSearchCV

from sklearn import metrics

from sklearn.neighbors import KNeighborsClassifier

from sklearn.dummy import DummyClassifier

from sklearn.ensemble import RandomForestClassifier

from strephit.commons.classification import reverse_gazetteer
from strephit.classification.feature_extractors import FeatureExtractor

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

    def fit(self, *training_sets):
        """ Searches for the best estimator and its arguments as well as the best
            training set amongst those specified.

            :param list training_sets: Training set to use. Should be a list
             of tuples (x, y) where x is the training set and y is the correct
             answer for each chunk
            :return: the best score, parameters and fitted model
            :rtype: tuple
        """
        best_training, best_score, best_params, best_model = None, None, None, None
        for i, (x, y) in enumerate(training_sets):
            for model, grid in self.models:
                if isclass(model):
                    model = model()

                search = GridSearchCV(model, param_grid=[grid], **self.kwargs)
                search.fit(x, y)

                if search.best_score_ > 0.99:
                    n = int(x.shape[0] * 0.1)
                    xte, yte, xtr, ytr = x[:n], y[:n], x[n:], y[n:]
                    m = model.__class__(**search.best_params_)
                    import pdb; pdb.set_trace()
                    m.fit(xtr, ytr)
                    yan = m.predict(xte)

                score, params, model = search.best_score_, search.best_params_, search.best_estimator_
                logger.debug('%s with parameters %s and training settings %d has score %s',
                             type(model), params, i, score)
                if best_score is None or score > best_score:
                    best_training, best_score, best_params, best_model = i, score, params, model

        return best_training, best_score, best_params, best_model


@click.command()
@click.argument('training-set', type=click.File('r'))
@click.argument('language')
@click.option('--gold-standard', type=click.File('r'))
@click.option('--gazetteer', type=click.File('r'), multiple=True)
@click.option('--n-folds', default=10)
@click.option('--n-jobs', default=1)
@click.option('--scoring', default='f1_weighted')
@click.option('--output', type=click.Path(dir_okay=False, writable=True),
              default='output/classifier_model.pkl', help='Where to save the model')
@click.option('--test', is_flag=True, help='Only try a small subset of the models')
def main(training_set, language, gold_standard, gazetteer, n_folds, n_jobs, scoring, output, test):
    """ Searches for the best hyperparameters """

    logger.info('Building training sets')

    # prepare the training sets by varying the gazetteer and the feature extractor
    training_sets, training_set_settings = [], []
    extractor_args = itertools.product([True, False], [0, 1, 2])
    for gaz in list(gazetteer) + [None]:
        for args in extractor_args:
            logger.debug('%d) gazetteer: %s, extractor params: %s',
                         len(training_set_settings), gaz.name if gaz else None, args)

            extractor = FeatureExtractor(language, *args)
            gazetteer = reverse_gazetteer(json.load(gazetteer)) if gaz else {}

            training_set.seek(0)
            for row in training_set:
                data = json.loads(row)
                extractor.process_sentence(data['sentence'], data['fes'],
                                           add_unknown=True, gazetteer=gazetteer)
            x, y = extractor.get_features(refit=True)
            training_sets.append((x, y))
            training_set_settings.append((gaz, extractor))

    # search over the parameter space and the different models
    logger.info('Searching for the best model parameters')
    models = [
        (KNeighborsClassifier, {
            'weights': ['uniform', 'distance'],
        }),
    ] + ([
        (LinearSVC, {
            'C': [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0],
            'multi_class': ['ovr', 'crammer_singer'],
        }),
        (SVC, {
            'C': [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0],
            'kernel': ['linear', 'poly', 'rbf', 'sigmoid'],
            'decision_function_shape': ['ovr', 'ovo'],
        }),
        (RandomForestClassifier, {
            'criterion': ['gini', 'entropy'],
            'min_samples_split': [1, 2, 5, 10, 25],
            'min_samples_leaf': [1, 2, 5, 10, 25],
            'n_estimators': [1, 2, 5, 10, 25, 50, 100, 250, 1000],
        })
    ] if not test else [])

    search = MultimodelGridSearchCV(*models, scoring=scoring, cv=n_folds, n_jobs=n_jobs)
    best_training, best_score, best_params, best_model = search.fit(*training_sets)
    gazetteer, extractor = training_set_settings[best_training]

    logger.info('Evaluation Results')
    logger.info('  Best model: %s', best_model.__class__.__name__)
    logger.info('  Score: %f', best_score)
    logger.info('  Parameters: %s', best_params)
    logger.info('  Gazetteer: %s', gazetteer)
    logger.info('  Extractor: %s', extractor)

    joblib.dump((best_model, extractor), output)
    logger.info("Done, dumped model to '%s'", output)

    if not gold_standard:
        logger.info('Skipping gold standard evaluation')
        return

    logger.info('Evaluating on the gold standard')

    x, y = training_set[best_training]

    for row in gold_standard:
        data = json.loads(row)
        extractor.process_sentence(data['sentence'], data['fes'], add_unknown=False, gazetteer=gazetteer)
    x_gold, y_gold = extractor.get_features(refit=False)

    dummy = DummyClassifier(strategy='stratified')
    dummy.fit(x, y)

    y_dummy = dummy.predict(x_gold)
    logger.info('Dummy model has a weighted-averaged F1 on the gold standard of %.4f',
                metrics.f1_score(y_gold, y_dummy, average='weighted'))

    y_best = best_model.predict(x_gold)
    logger.info('Best model has a weighted-averaged F1 on the gold standard of %.4f',
                metrics.f1_score(y_gold, y_best, average='weighted'))
