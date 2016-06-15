# -*- coding: utf-8 -*-
import itertools
import sqlite3
import json
import logging
import datetime

import scrapy
from scrapy import Request

from strephit.web_sources_corpus.items import WebSourcesCorpusItem

logger = logging.getLogger(__name__)


class VocabGettyEduSpider(scrapy.Spider):
    name = "vocab_getty_edu"
    allowed_domains = ["vocab.getty.edu"]

    # their wonderful SPARQL endpoint does not perform OPTIONAL queries correctly and crashes when using OFFSET+LIMIT
    # so, instead of using a single query with seven OPTIONAL clauses and pagination we will use seven queries
    # without pagination.
    # Partial results will be collected in a SQLite database and aggregated with a seven-tables LEFT OUTER JOIN
    name_query          = 'http://vocab.getty.edu/sparql.csv?query=SELECT+%3Fperson+%3Fname%0D%0AWHERE+%7B%0D%0A%3F' \
                          'person+rdf%3Atype+gvp%3APersonConcept%3B%0D%0A++++++++gvp%3AprefLabelGVP+%3Flabel.%0D%0A' \
                          '%3Flabel+gvp%3Aterm+%3Fname%0D%0A%7D&_implicit=false&_equivalent=false&_form=%2Fsparql'
    bio_query           = 'http://vocab.getty.edu/sparql.csv?query=SELECT+%3Fperson+%3Fbio2%0D%0AWHERE+%7B%0D%0A%3F' \
                          'person+rdf%3Atype+gvp%3APersonConcept%3B%0D%0A++++++++skos%3AscopeNote+%3Fnote.%0D%0A+%3' \
                          'Fnote+rdf%3Avalue+%3Fbio2.%0D%0A%7D&_implicit=false&_equivalent=false&equivalent=true&_f' \
                          'orm=%2Fsparql'
    bio_query_2         = 'http://vocab.getty.edu/sparql.csv?query=SELECT+%3Fperson+%3FshortBio%0D%0AWHERE+%7B%0D%0' \
                          'A%3Fperson+rdf%3Atype+gvp%3APersonConcept%3B%0D%0A++++++++foaf%3Afocus+%3Ffocus.%0D%0A+%' \
                          '3Ffocus+gvp%3AbiographyPreferred+%3Fbio.%0D%0A+%3Fbio+schema%3Adescription+%3FshortBio.%' \
                          '0D%0A%7D&_implicit=false&_equivalent=false&equivalent=true&_form=%2Fsparql'
    nationality_query   = 'http://vocab.getty.edu/sparql.csv?query=SELECT+%3Fperson+%3Fnationality%0D%0AWHERE+%7B%0' \
                          'D%0A%3Fperson+rdf%3Atype+gvp%3APersonConcept%3B%0D%0A++++++++foaf%3Afocus+%3Ffocus.%0D%0' \
                          'A+%3Ffocus+gvp%3AnationalityPreferred+%3Fny.%0D%0A+%3Fny+gvp%3AprefLabelGVP+%3FlblNation' \
                          'ality.%0D%0A+%3FlblNationality+gvp%3Aterm+%3Fnationality.+%0D%0A%7D&_implicit=false&_equ' \
                          'ivalent=false&equivalent=true&_form=%2Fsparql'
    birth_year_query    = 'http://vocab.getty.edu/sparql.csv?query=SELECT+%3Fperson+%3Fbirth%0D%0AWHERE+%7B%0D%0A%3' \
                          'Fperson+rdf%3Atype+gvp%3APersonConcept%3B%0D%0A++++++++foaf%3Afocus+%3Ffocus.%0D%0A+%3Ff' \
                          'ocus+gvp%3AbiographyPreferred+%3Fbio.%0D%0A+%3Fbio+gvp%3AestStart+%3Fbirth.%0D%0A%7D&_im' \
                          'plicit=false&_equivalent=false&equivalent=true&_form=%2Fsparql'
    birth_place_query   = 'http://vocab.getty.edu/sparql.csv?query=SELECT+%3Fperson+%3FdeathPlace%0D%0AWHERE+%7B%0D' \
                          '%0A%3Fperson+rdf%3Atype+gvp%3APersonConcept%3B%0D%0A++++++++foaf%3Afocus+%3Ffocus.%0D%0A' \
                          '+%3Ffocus+gvp%3AbiographyPreferred+%3Fbio.%0D%0A+%3Fbio+schema%3AdeathPlace+%3Fdpf.%0D%0' \
                          'A+%3Fdp+foaf%3Afocus+%3Fdpf%3B%0D%0A++++++gvp%3AparentString+%3FdeathPlace.%0D%0A%7D&_im' \
                          'plicit=false&implicit=true&_equivalent=false&_form=%2Fsparql'
    death_year_query    = 'http://vocab.getty.edu/sparql.csv?query=SELECT+%3Fperson+%3Fdeath%0D%0AWHERE+%7B%0D%0A%3' \
                          'Fperson+rdf%3Atype+gvp%3APersonConcept%3B%0D%0A++++++++foaf%3Afocus+%3Ffocus.%0D%0A+%3Ff' \
                          'ocus+gvp%3AbiographyPreferred+%3Fbio.%0D%0A+%3Fbio+gvp%3AestEnd+%3Fdeath%3B%0D%0A%7D&_im' \
                          'plicit=false&_equivalent=false&equivalent=true&_form=%2Fsparql'
    death_place_query   = 'http://vocab.getty.edu/sparql.csv?query=SELECT+%3Fperson+%3FbirthPlace%0D%0AWHERE+%7B%0D' \
                          '%0A%3Fperson+rdf%3Atype+gvp%3APersonConcept%3B%0D%0A++++++++foaf%3Afocus+%3Ffocus.%0D%0A' \
                          '+%3Ffocus+gvp%3AbiographyPreferred+%3Fbio.%0D%0A+%3Fbio+schema%3AbirthPlace+%3Fbpf.%0D%0' \
                          'A+%3Fbp+foaf%3Afocus+%3Fbpf%3B%0D%0A++++++gvp%3AparentString+%3FbirthPlace.%0D%0A%7D&_im' \
                          'plicit=false&implicit=true&_equivalent=false&_form=%2Fsparql'
    gender_query        = 'http://vocab.getty.edu/sparql.csv?query=SELECT+%3Fperson+%3Fgender%0D%0AWHERE+%7B%0D%0A%' \
                          '3Fperson+rdf%3Atype+gvp%3APersonConcept%3B%0D%0A++++++++foaf%3Afocus+%3Ffocus.%0D%0A+%3F' \
                          'focus+gvp%3AbiographyPreferred+%3Fbio.%0D%0A+%3Fbio+schema%3Agender+%3Fgender%3B%0D%0A%7' \
                          'D&_implicit=false&_equivalent=false&equivalent=true&_form=%2Fsparql'

    queries = [
        ('name', name_query),
        ('bio', bio_query),
        ('bio2', bio_query_2),
        ('nationality', nationality_query),
        ('birth_year', birth_year_query),
        ('birth_place', birth_place_query),
        ('death_year', death_year_query),
        ('death_place', death_place_query),
        ('gender', gender_query),
    ]

    completed_queries = set()
    db_connection = sqlite3.connect(':memory:')  # no worries, only a couple of hundreds of MBs

    def start_requests(self):
        for table, query_url in self.queries:
            self.db_connection.execute('DROP TABLE IF EXISTS %s' % table)
            self.db_connection.execute('CREATE TABLE %s(pk VARCHAR(40), data TEXT)' % table)
            self.db_connection.commit()
            yield Request(query_url, self.load_into_db(table))

    def load_into_db(self, table):
        def callback(response):
            """ Loads the CSV data contained into the response body and puts it into the appropriate table
            """
            data = itertools.ifilter(lambda x: len(x) == 2,
                                     (row.split(',', 1) for row in response.body_as_unicode().split('\r\n')[1:]))

            cur = self.db_connection.cursor()
            try:
                cur.executemany('INSERT INTO %s(pk, data) VALUES (?, ?)' % table, data)
            except sqlite3.Error:
                self.db_connection.rollback()
                raise
            else:
                self.db_connection.commit()
            finally:
                cur.close()

            for each in self.finalize_data(table):
                yield each
        return callback

    def finalize_data(self, table):
        """ This method will be called after `table` has been populated. When all tables have been
            populated with data joins them and yields the polished items.
        """
        self.completed_queries.add(table)
        if len(self.completed_queries) < len(self.queries):
            return

        table_names = map(lambda (table, _): table, self.queries)
        table_aliases = 'abcdefghijklmnopqrstuvwxyz'[:len(self.queries)]

        fields = 'a.pk, ' + ', '.join('{}.data'.format(t) for t in table_aliases)
        join = '{} AS a '.format(table_names[0]) + ' '.join(
            'LEFT OUTER JOIN {table} AS {name} ON a.pk = {name}.pk'.format(table=table, name=alias)
            for table, alias in zip(table_names, table_aliases)[1:]
        )

        query = 'SELECT {fields} FROM {join}'.format(fields=fields, join=join)

        cur = self.db_connection.cursor()
        cur.execute(query)

        for row in iter(cur.fetchone, None):
            try:
                yield self.row_to_item(row)
            except:
                logger.exception('while serializing item')

        cur.close()

    def row_to_item(self, row):
        """ Converts a single row, result of the join between all tables, into a finished item
        """
        this_year = datetime.date.today().year

        cleaned = []
        for i, field in enumerate(row):
            if not field:
                cleaned.append(field)
            elif field[0] == '"' and field[-1] == '"':
                cleaned.append(field[1:-1].replace('\\"', '"'))
            elif i == 5 or i == 7:
                try:
                    n = int(field)
                    # they estimate the death date of living people as birth date + 100
                    # of course we don't want this kind of data here
                    if n > this_year:
                        raise ValueError()
                    else:
                        cleaned.append(field)
                except ValueError:
                    cleaned.append(None)
            else:
                cleaned.append(field)

        url, name, bio1, bio2, nationality, birth_year, birth_place, death_year, death_place, gender = cleaned
        url = url.replace('http://vocab.getty.edu/ulan/', 'http://vocab.getty.edu/page/ulan/')
        gender = {
            'http://vocab.getty.edu/aat/300189557': 'female',
            'http://vocab.getty.edu/aat/300189559': 'male',
        }.get(gender)

        return WebSourcesCorpusItem(
            url=url,
            name=name,
            birth=birth_year,
            death=death_year,
            bio=u'{}\n{}'.format(bio1 or '', bio2 or '').strip(),
            other=json.dumps({
                'birth_place': birth_place,
                'death_place': death_place,
                'gender': gender,
                'nationality': nationality,
            })
        )
