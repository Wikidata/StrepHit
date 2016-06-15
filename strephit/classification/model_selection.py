# -*- encoding: utf-8 -*-
import json
import logging

import click
from sklearn.svm import LinearSVC
from sklearn.grid_search import GridSearchCV
from sklearn import metrics

from sklearn.dummy import DummyClassifier

from strephit.commons.classification import reverse_gazetteer
from strephit.classification.feature_extractors import FactExtractorFeatureExtractor

logger = logging.getLogger(__name__)


@click.command()
@click.argument('training-set', type=click.File('r'))
@click.argument('language')
@click.option('--gold-standard', type=click.File('r'))
@click.option('--gazetteer', type=click.File('r'))
def main(training_set, language, gold_standard, gazetteer):
    """ Searches for the best hyperparameters """

    gazetteer = reverse_gazetteer(json.load(gazetteer)) if gazetteer else {}

    logger.info('Building training set')
    extractor = FactExtractorFeatureExtractor(language)
    for row in training_set:
        data = json.loads(row)
        extractor.process_sentence(data['sentence'], data['fes'],
                                   add_unknown=True, gazetteer=gazetteer)

    logger.info('Finalizing training set')
    x, y = extractor.get_features()

    logger.info('Searching for the best model parameters')
    svc = LinearSVC()
    search = GridSearchCV(
        svc,
        param_grid=[{
            'C': [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0],
            'multi_class': ['ovr', 'crammer_singer'],
        }],
        scoring='f1_weighted',
        cv=10)
    search.fit(x, y)

    logger.info('The best model (weighted-averaged F1 of %.4f) has parameters %s',
                search.best_score_, search.best_params_)

    if not gold_standard:
        logger.info('Skipping gold standard evaluation')
        return

    logger.info('Evaluating on the gold standard')
    for row in gold_standard:
        data = json.loads(row)
        extractor.process_sentence(data['sentence'], data['fes'])
    x_gold, y_gold = extractor.get_features()

    dummy = DummyClassifier(strategy='stratified')
    dummy.fit(x, y)

    y_dummy = dummy.predict(x_gold)
    logger.info('Dummy model has a weighted-averaged F1 on the gold standard of %.4f',
                metrics.f1_score(y_gold, y_dummy, average='weighted'))

    y_best = search.predict(x_gold)
    logger.info('Best model has a weighted-averaged F1 on the gold standard of %.4f',
                metrics.f1_score(y_gold, y_best, average='weighted'))
