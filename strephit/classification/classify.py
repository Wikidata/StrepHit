# -*- encoding: utf-8 -*-
import json
import logging

import click

from sklearn.externals import joblib

from strephit.commons.classification import apply_custom_classification_rules, reverse_gazetteer
from strephit.commons import parallel

logger = logging.getLogger(__name__)


class SentenceClassifier:
    """ Supervised Sentence classifier
    """

    def __init__(self, model, extractor, language, gazetteer):
        self.model = model
        self.language = language
        self.extractor = extractor
        self.gazetteer = gazetteer

    def classify_sentences(self, sentences):
        """ Classify the given sentences

            :param list sentences: sentences to be classified. Each one
             should be a dict with a `text`, a source `url` and some `linked_entities`
            :return: Classified sentences with the recognized `fes`
            :rtype: generator of dicts
        """
        self.extractor.start()

        sentences_data = []
        for data in sentences:
            if 'url' not in data:
                logger.warn('found a sentence with no URL (row number %d), skipping it')
                continue

            entities = dict(enumerate(e['chunk'] for e in data.get('linked_entities', [])))
            tagged = self.extractor.process_sentence(
                data['text'], entities, add_unknown=False, gazetteer=self.gazetteer
            )

            data['tagged'] = tagged
            sentences_data.append(data)

        features, _ = self.extractor.get_features()
        y = self.model.predict(features)

        token_offset = 0
        role_label_to_index = self.extractor.role_index.items
        role_index_to_label = self.extractor.role_index.reverse_map()

        for data in sentences_data:
            fes = []
            for each in data['tagged']:
                chunk = each[0]
                predicted_role = y[token_offset]

                if predicted_role != role_label_to_index['O']:
                    label = role_index_to_label[predicted_role]
                    logger.debug('chunk "%s" classified as "%s"', chunk, label)
                    fes.append({
                        'chunk': chunk,
                        'fe': label,
                    })
                    # TODO
                    # do not group entities into a single chunk, and after classification
                    # check if the word is contained in an entity; if so, assign the label
                    # to the whole entity

                token_offset += 1

            logger.debug('found %d FEs in sentence "%s"', len(fes), data['text'])
            if fes:
                classified = {
                    'lu': data['lu'],
                    'name': data['name'],
                    'url': data['url'],
                    'text': data['text'],
                    'fes': fes,
                    'linked_entities': data.get('linked_entities', []),
                }

                final = apply_custom_classification_rules(classified, self.language)
                yield final


@click.command()
@click.argument('sentences', type=click.File('r'))
@click.argument('model', type=click.Path(dir_okay=False, writable=True))
@click.argument('language')
@click.option('--outfile', '-o', type=click.File('w'), default='output/supervised_classified.jsonlines')
@click.option('--processes', '-p', default=0)
@click.option('--gazetteer', type=click.File('r'))
def main(sentences, model, language, outfile, processes, gazetteer):
    gazetteer = reverse_gazetteer(json.load(gazetteer)) if gazetteer else {}

    logger.info("Loading model from '%s' ...", model)
    model, extractor = joblib.load(model)

    classifier = SentenceClassifier(model, extractor, language, gazetteer)

    def worker(batch):
        data = (json.loads(s) for s in batch)
        for classified in classifier.classify_sentences(data):
            yield json.dumps(classified)

    count = 0
    for each in parallel.map(worker, sentences, batch_size=1000,
                             flatten=True, processes=processes):
        outfile.write(each)
        outfile.write('\n')

        count += 1
        if count % 1000 == 0:
            logger.info('Classified %d sentences', count)

    logger.info('Done, classified %d sentences', count)
    logger.info("Classified sentences dumped to '%s'", outfile.name)
