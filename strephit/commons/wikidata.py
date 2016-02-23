from __future__ import absolute_import
import json
import logging
from datetime import datetime
from collections import defaultdict
from strephit.commons import cache, io, datetime


logger = logging.getLogger(__name__)


WIKIDATA_API_URL = 'https://www.wikidata.org/w/api.php'
PROPERTY_TO_WIKIDATA = {
    'Died of:': 'P509',  # check
    'Patronage': '',
    'Marriage': 'P26',  # check
    'Last Name': 'P734',
    'Children': 'P40',  # check
    'Place of death': 'P20',
    'Relatives': 'P1038',  # check
    'Year died': 'P570',
    'Collaborators': '',
    'Published sources': '',
    'alt. Names': 'P742',
    'Country of Activity': '',
    'Year born': 'P569',
    'Sample(s)': '',
    'Given Name': 'P735',
    'First name(s)': 'P735',
    'other': '',
    'Worked for': 'P108',  # check
    'Techniques': '',
    'biography': '',
    'title': 'P97',  # check
    'Principal Co-Consecrators:': '',
    'Principal Consecrator:': '',
    'Episcopal Lineage / Apostolic Succession:': '',
    'http://erlangen-crm.org/current/P12i_was_present_at': '',
    'microdata': '',
    'bio': '',
    'how-to-cite': '',
    'oup': '',
    'short-desc': '',
    'sources': '',
    'http://erlangen-crm.org/current/P100_died_in': '',
    'http://erlangen-crm.org/current/P98i_was_born': '',
    'http://collection.britishmuseum.org/id/ontology/PX_profession': 'P106',
    'http://collection.britishmuseum.org/id/ontology/PX_nationality': 'P27',
    'http://erlangen-crm.org/current/P3_has_note': '',
    'http://collection.britishmuseum.org/id/ontology/PX_gender': 'P21',
    'http://erlangen-crm.org/current/P131_is_identified_by': 'P742',  # check
    'http://www.w3.org/2004/02/skos/core#inScheme': '',
    'http://www.w3.org/2004/02/skos/core#prefLabel': '',
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#type': '',
    'Place of origin:': 'P19',  # check
    'Gender:': 'P21',
    'Age:': '',
    'trivia': '',
    'death': 'P570',
    'birth': 'P569',
    'name': 'P1477',
    'honorific': 'P1035',
}


PROPERTY_RESOLVERS = {}
def resolver(*properties):
    """ Decorator to register a class as resolver for the given property.
    """
    def decorator(function):
        for property in properties:
            if property in PROPERTY_RESOLVERS:
                logger.error('multiple resolvers registered for property %s, ' \
                             'only the last one will be kept' % property)
            PROPERTY_RESOLVERS[property] = function
        return function
    return decorator


def resolve(property, value, language):
    """ Tries to resolve (i.e. serialize in an appropriate format) an object
        instance of the given property.
    """
    if property in PROPERTY_RESOLVERS:
        return PROPERTY_RESOLVERS[property](property, value, language)
    else:
        val  = identity_resolver(property, value, language)  # fixme remove once mapping is done
        return '"%s"' % val if val else None
        logger.warn("don't know how to resolve value %s of property %s" % (
            repr(value), property
        ))
        return None


@resolver('P1035')
def identity_resolver(property, value, language):
    return value


@cache.cached
@resolver('P21')
def gender_resolver(property, value, language):
    """ Resolve gender """
    results = search(value, language)
    if results and results[0]['label'] in {'male', 'female'}:
        return results[0]['id']
    else:
        return None


@cache.cached
@resolver('P19')
def place_resolver(property, value, language):
    """ Resolves place names """
    results = search(value, language)
    if results:
        _id = results[0]['id']
        cache.set(language + property + value, _id)
        return _id
    else:
        logger.warn('cannot resolve %s (%s)' % (value, property))
        return ''  # cache, but do not serialize


@cache.cached
@resolver('P569', 'P570')
def date_resolver(property, value, language):
    value = value.lower().replace('(circa)', '').replace('(probable)', '') \
                .replace('(presumed)', '').strip()
    if not value:
        return None
    try:
        res = datetime.parse(value)
        return format_date(res)
    except ValueError:
        logger.debug('cannot parse date ' + value)
        return None


def call_api(action, cache=True, **kwargs):
    """ Invoke the given method of wikidata APIs with the given parameters
    """
    kwargs['format'] = 'json'
    kwargs['action'] = action
    resp = io.get_and_cache(WIKIDATA_API_URL, use_cache=cache, params=kwargs)
    return json.loads(resp)


def search(term, language):
    return call_api('wbsearchentities', search=term, language=language).get('search', [])


def finalize_statement(subject, property, value, language, url=None,
                       resolve_property=True):
    """ Given the components of a statement, convert it into a quick statement.
    """
    if resolve_property:
        property = PROPERTY_TO_WIKIDATA.get(property)

    if not property or value is None:
        return None
    
    value = resolve(property, value.replace('\n', ' '), language)
    if not value:
        return None

    statement = '%s\t%s\t%s' % (subject, property, value)
    if url:
        pass  # fixme add statement source

    return statement


def format_date(date):
    """ Formats a date according to Wikidata syntax
        :param date: dictionary with keys `year`, `month` and `day`
    """
    year, month, day = date.get('year'), date.get('month'), date.get('day')
    if day:
        precision = 11
    elif month:
        precision = 10
    elif year:
        precision = 9
    else:
        raise ValueError('empty date')

    if year and month and day:
        return '+0000000%s-%s-%sT00:00:00Z/%s' % (year, month, day, precision)
    elif year and month and not day:
        return '+0000000%s-%s-01T00:00:00Z/%s' % (year, month, precision)
    elif year and not month and not day:
        return '+0000000%s-01-01T00:00:00Z/%s' % (year, precision)
    elif not year and month and day:
        return '+00000000000-%s-%sT00:00:00Z/%s' % (year, month, precision)
    else:
        raise ValueError('don\'t know how to format' + date)
