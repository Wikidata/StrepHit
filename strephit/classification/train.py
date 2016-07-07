# -*- encoding: utf-8 -*-
import json
import logging
from importlib import import_module
from inspect import getargspec
import click
from sklearn.dummy import DummyClassifier
from sklearn.externals import joblib
from sklearn.cross_validation import KFold
from strephit.commons.classification import reverse_gazetteer
from strephit.classification.model_selection import Scorer
from strephit.classification.classifiers import FeatureSelectedClassifier
import numpy as np

logger = logging.getLogger(__name__)


def initialize(cls_name, args, call_init):
    path = cls_name.split('.')
    module = '.'.join(path[:-1])
    cls = getattr(import_module(module), path[-1])
    arg_names, _, _, arg_default = getargspec(cls.__init__)
    defaults = dict(zip(reversed(arg_names), reversed(arg_default)))

    init_args = {}
    for k, v in args:
        convert = type(defaults[k])
        if isinstance(convert, type(None)):
            raise ValueError('cannot specify %s parameter', k)
        elif isinstance(convert, bool):
            convert = lambda s: s.lower() in {'t', 'y', 'true', 'yes'}

        init_args[k] = convert(v)

    return cls(**init_args) if call_init else (cls, init_args)


def kfolds_evaluation(folds, model, scorer, x, y):
    kf = KFold(x.shape[0], folds, shuffle=True)

    scores_dummy, scores_test, scores_train = [], [], []
    for train_index, test_index in kf:
        x_train, y_train = x[train_index], y[train_index]
        x_test, y_test = x[test_index], y[test_index]

        model.fit(x_train, y_train)
        dummy = DummyClassifier()
        dummy.fit(x_train, y_train)

        scores_test.append(scorer(model, x_test, y_test))
        scores_dummy.append(scorer(dummy, x_test, y_test))
        scores_train.append(scorer(model, x_train, y_train))

    logger.info('%d-folds cross evaluation results', folds)
    logger.info('    minimum test %f  dummy %f  training %f',
                min(scores_test), min(scores_dummy), min(scores_train))

    logger.info('    maximum test %f  dummy %f  training %f',
                max(scores_test), max(scores_dummy), max(scores_train))
    logger.info('    average test %f  dummy %f  training %f',
                np.average(scores_test), np.average(scores_dummy), np.average(scores_train))
    logger.info('    median  test %f  dummy %f  training %f',
                np.median(scores_test), np.median(scores_dummy), np.median(scores_train))

    logger.debug('full test scores: %s', scores_test)
    logger.debug('full dummy scores: %s', scores_dummy)
    logger.debug('full train scores: %s', scores_train)


@click.command()
@click.argument('training-set', type=click.File('r'))
@click.argument('language')
@click.option('-o', '--outfile', type=click.Path(dir_okay=False, writable=True),
              default='output/classifier_model.pkl', help='Where to save the model')
@click.option('--model-class', default='sklearn.svm.SVC')
@click.option('--model-param', '-p', type=(unicode, unicode), multiple=True,
              help='kwargs for the model. See scikit doc',
              default=[('kernel', 'linear'), ('C', '0.15')])
@click.option('--extractor-class', default='strephit.classification.feature_extractors.BagOfTermsFeatureExtractor')
@click.option('--extractor-param', '-P', type=(unicode, unicode), multiple=True,
              help='extrator kwargs',
              default=[('window_width', '2'), ('collapse_fes', 'true')])
@click.option('--gazetteer', type=click.File('r'))
@click.option('--folds', default=0, help='Perform k-fold evaluation before training on full data')
@click.option('--scoring', default='macro')
@click.option('--skip-majority', is_flag=True)
def main(training_set, language, outfile, model_class, model_param, extractor_class,
         extractor_param, gazetteer, folds, scoring, skip_majority):
    """ Trains the classifier """

    gazetteer = reverse_gazetteer(json.load(gazetteer)) if gazetteer else {}
    extractor = initialize(extractor_class, [('language', language)] + list(extractor_param), True)

    logger.info("Building training set from '%s' ..." % training_set.name)
    for row in training_set:
        data = json.loads(row)
        extractor.process_sentence(data['sentence'], data['lu'], data['fes'],
                                   add_unknown=True, gazetteer=gazetteer)
    x, y = extractor.get_features(refit=True)
    logger.info('Got %d samples with %d features each', *x.shape)

    if folds > 1:
        model_cls, model_args = initialize(model_class, model_param, False)
        model = FeatureSelectedClassifier(model_cls, extractor.lu_column(), model_args)
        scorer = Scorer(scoring, skip_majority)
        kfolds_evaluation(folds, model, scorer, x, y)

    logger.info('Fitting model ...')
    model_cls, model_args = initialize(model_class, model_param, False)
    model = FeatureSelectedClassifier(model_cls, extractor.lu_column(), model_args)
    model.fit(x, y)

    joblib.dump((model, {
        'extractor': extractor
    }), outfile)

    logger.info("Done, dumped model to '%s'", outfile)
