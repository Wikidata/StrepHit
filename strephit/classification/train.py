# -*- encoding: utf-8 -*-
import json
import logging

import click

from strephit.classification.feature_extractors import FactExtractorFeatureExtractor

logger = logging.getLogger(__name__)


@click.command()
@click.argument('training-set', type=click.File('r'))
@click.argument('language')
def main(training_set, language):
    """ Train the classifier """

    extractor = FactExtractorFeatureExtractor(language)

    all_features = []
    for row in training_set:
        data = json.loads(row)
        all_features.extend(extractor.extract_features(data))

        # TODO actual training...
