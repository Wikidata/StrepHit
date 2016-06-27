# -*- encoding: utf-8 -*-
import json
import logging
from importlib import import_module
from inspect import getargspec

import click
from sklearn.externals import joblib

from strephit.commons.classification import reverse_gazetteer

logger = logging.getLogger(__name__)


def initialize(cls_name, args):
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

    return cls(**init_args)


@click.command()
@click.argument('training-set', type=click.File('r'))
@click.argument('language')
@click.option('-o', '--outfile', type=click.Path(dir_okay=False, writable=True),
              default='output/classifier_model.pkl', help='Where to save the model')
@click.option('--model', default='sklearn.svm.LinearSVC')
@click.option('--model-param', '-p', type=(unicode, unicode), multiple=True,
              help='kwargs for the model. See scikit doc',
              default=[('multi_class', 'ovr'), ('C', '1.0')])
@click.option('--extractor', default='strephit.classification.feature_extractors.BagOfTermsFeatureExtractor')
@click.option('--extractor-param', '-P', type=(unicode, unicode),
              help='extrator kwargs',
              default=[('window_width', '2'), ('collapse_fes', 'true')])
@click.option('--gazetteer', type=click.File('r'))
def main(training_set, language, outfile, model, model_param, extractor, extractor_param, gazetteer):
    """ Trains the classifier """

    gazetteer = reverse_gazetteer(json.load(gazetteer)) if gazetteer else {}
    extractor = initialize(extractor, [('language', 'en')] + list(extractor_param))
    model = initialize(model, model_param)

    logger.info("Building training set from '%s' ..." % training_set.name)
    for row in training_set:
        data = json.loads(row)
        extractor.process_sentence(data['sentence'], data['lu'], data['fes'],
                                   add_unknown=True, gazetteer=gazetteer)
    x, y = extractor.get_features(refit=True)
    logger.info('Got %d samples with %d features each', *x.shape)

    logger.info('Fitting model ...')
    model.fit(x, y)

    joblib.dump((model, {
        'extractor': extractor
    }), outfile)

    logger.info("Done, dumped model to '%s'", outfile)
