#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import click
import json
import logging
from web_sources_corpus import utils


logger = logging.getLogger(__name__)


query_url = 'http://collection.britishmuseum.org/sparql.json?query=PREFIX+rdf%3A+%3C' \
            'http%3A%2F%2Fwww.w3.org%2F1999%2F02%2F22-rdf-syntax-ns%23%3E%0D%0APREFI' \
            'X+skos%3A+%3Chttp%3A%2F%2Fwww.w3.org%2F2004%2F02%2Fskos%2Fcore%23%3E%0D' \
            '%0APREFIX+bmo%3A+%3Chttp%3A%2F%2Fcollection.britishmuseum.org%2Fid%2Fon' \
            'tology%2F%3E%0D%0APREFIX+ecrm%3A+%3Chttp%3A%2F%2Ferlangen-crm.org%2Fcur' \
            'rent%2F%3E%0D%0APREFIX+rdfs%3A+%3Chttp%3A%2F%2Fwww.w3.org%2F2000%2F01%2' \
            'Frdf-schema%23%3E%0D%0A%0D%0ASELECT+%3Fperson+%3Fname+%3Fgender+%3FlblN' \
            'ationality+%3Fbio+%3FlblProfession+%3FlblIdentifier+%3FlblDeath+%3FlblB' \
            'irth%0D%0AWHERE+%7B+%0D%0A+++%3Fperson+rdf%3Atype+ecrm%3AE21_Person.%0D' \
            '%0A+++%0D%0A++++OPTIONAL+%7B+%3Fperson+skos%3AprefLabel+%3Fname.+%7D%0D' \
            '%0A++++OPTIONAL+%7B+%3Fperson+bmo%3APX_gender+%3Fgender.+%7D%0D%0A++++O' \
            'PTIONAL+%7B+%3Fperson+bmo%3APX_nationality+%3Fnationality.%0D%0A+++++++' \
            '++++++++%3Fnationality+skos%3AprefLabel+%3FlblNationality.+%7D%0D%0A+++' \
            '+OPTIONAL+%7B+%3Fperson+ecrm%3AP3_has_note+%3Fbio.+%7D%0D%0A++++OPTIONA' \
            'L+%7B+%3Fperson+bmo%3APX_profession+%3Fprofession.%0D%0A+++++++++++++++' \
            '%3Fprofession+rdfs%3Alabel+%3FlblProfession.+%7D%0D%0A++++OPTIONAL+%7B+' \
            '%3Fperson+ecrm%3AP131_is_identified_by+%3Fidentifier.%0D%0A++++++++++++' \
            '+++%3Fidentifier+rdfs%3Alabel+%3FlblIdentifier.+%7D+%0D%0A++++OPTIONAL+' \
            '%7B+%3Fperson+ecrm%3AP100_died_in+%3Fdeath.%0D%0A+++++++++++++++%3Fdeat' \
            'h+ecrm%3AP4_has_time-span+%3Fdeath_ts.%0D%0A+++++++++++++++%3Fdeath_ts+' \
            'rdfs%3Alabel+%3FlblDeath.+%7D%0D%0A++++OPTIONAL+%7B+%3Fperson+ecrm%3AP9' \
            '8i_was_born+%3Fbirth.%0D%0A+++++++++++++++%3Fbirth+ecrm%3AP4_has_time-s' \
            'pan+%3Fbirth_ts.%0D%0A+++++++++++++++%3Fbirth_ts+rdfs%3Alabel+%3FlblBir' \
            'th.+%7D%0D%0A++++%0D%0A%7D%0D%0A+%0D%0ALIMIT+{limit}%0D%0AOFFSET+{offse' \
            't}%0D%0A&_implicit=false&implicit=true&_equivalent=false&equivalent=tru' \
            'e&_form=%2Fsparql'


def serialize_person(person):
    def default_serializer(obj):
        """ provides a custom serializer for sets """
        if isinstance(obj, set):
            if len(obj) == 1:
                return obj.pop()
            else:
                return list(obj)
        else:
            raise TypeError

    return json.dumps({
        'url': person.pop('url'),
        'birth': person.pop('lblBirth', None),
        'death': person.pop('lblDeath', None),
        'bio': '\n'.join(person.pop('bio', '')) or None,
        'name': ' '.join(person.pop('name', '')) or None,
        'other': person,
    }, default=default_serializer)


@click.command()
@click.argument('out-file', type=click.File('w'))
@click.option('--use-cache/--no-cache', default=True)
@click.option('--step', '-s', default=1000)
def main(out_file, use_cache, step):
    finished = False
    offset = 0
    person = {}
    while not finished:
        print 'processed %d records' % offset
        url = query_url.format(limit=step, offset=offset)
        result = json.loads(utils.get_and_cache(url, use_cache))
        offset += step
        finished = len(result['results']['bindings']) < step

        # adjacent records can refer to the same person, so group all properties in sets
        for i, data in enumerate(result['results']['bindings']):
            url = data.pop('person')['value']

            if person and person['url'] != url:
                out_file.write(serialize_person(person))
                out_file.write('\n')
                person = {}

            person['url'] = url
            for key, value in data.iteritems():
                value = value['value']
                if key == 'gender':
                    value = value.split('/')[-1]

                if key in person:
                    person[key].add(value)
                else:
                    person[key] = {value}


if __name__ == '__main__':
    main()
