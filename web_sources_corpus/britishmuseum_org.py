#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import click
import json
import progressbar
from web_sources_corpus import utils

persons_query = 'http://collection.britishmuseum.org/sparql.json?query=PREFIX+crm%3A' \
                '+%3Chttp%3A%2F%2Ferlangen-crm.org%2Fcurrent%2F%3E%0D%0A%0D%0ASELECT' \
                '+%3Fp%0D%0A%7B+%0D%0A++%3Fp+rdf%3Atype+crm%3AE21_Person%0D%0A%7D%0D' \
                '%0ALIMIT+{limit}%0D%0AOFFSET+{offset}&_implicit=false&implicit=true' \
                '&_equivalent=false&_form=%2Fsparql'

count_query = 'http://collection.britishmuseum.org/sparql.json?query=PREFIX+crm%3A+' \
              '%3Chttp%3A%2F%2Ferlangen-crm.org%2Fcurrent%2F%3E%0D%0A%0D%0ASELECT+%' \
              '28count%28%3Fp%29+as+%3Fc%29%0D%0A%7B+%0D%0A++%3Fp+rdf%3Atype+crm%3A' \
              'E21_Person%0D%0A%7D&_implicit=false&implicit=true&_equivalent=false&' \
              '_form=%2Fsparql'


detail_url = 'http://collection.britishmuseum.org/resource?uri={person}&format=json'


@click.command()
@click.argument('out-file', type=click.File('w'))
@click.option('--use-cache/--no-cache', default=True)
@click.option('--step', '-s', default=1000)
def main(out_file, use_cache, step):
    result = json.loads(utils.get_and_cache(count_query))
    count = int(result['results']['bindings'][0]['c']['value'])

    with progressbar.ProgressBar(max_value=count) as bar:
        for offset in xrange(0, count, step):
            url = persons_query.format(limit=step, offset=offset)
            result = json.loads(utils.get_and_cache(url))
            for i, person in enumerate(result['results']['bindings']):
                person_url = person['p']['value']
                details = json.loads(utils.get_and_cache(detail_url.format(person=person_url)))
                data = details[person_url]
                item = {
                    'name': data['http://www.w3.org/2004/02/skos/core#prefLabel'][0]['value'],
                    'other': json.dumps(data)
                }
                if 'http://erlangen-crm.org/current/P3_has_note' in data:
                    item['bio'] = data['http://erlangen-crm.org/current/P3_has_note'][0]['value']
                out_file.write(json.dumps(item))
                out_file.write('\n')
                bar.update(offset + i)


if __name__ == '__main__':
    main()
