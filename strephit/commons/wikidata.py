from __future__ import absolute_import
import json
import logging
from datetime import datetime
from collections import defaultdict
from strephit.commons import cache, io, datetime, text


logger = logging.getLogger(__name__)


WIKIDATA_API_URL = 'https://www.wikidata.org/w/api.php'
PROPERTY_TO_WIKIDATA = {
    'Died of:': 'P509',
    'Marriage': 'P26',
    'Last Name': 'P734',
    'Children': 'P40',
    'Place of death': 'P20',
    'Relatives': 'P1038',
    'Year died': 'P570',
    'alt. Names': 'P742',
    'Year born': 'P569',
    'Given Name': 'P735',
    'First name(s)': 'P735',
    'Worked for': 'P108',
    'title': 'P97',
    'lblProfession': 'P106',
    'lblNationality': 'P27',
    'gender': 'P21',
    'lblIdentifier': 'P742',
    'Place of origin:': 'P19',
    'Gender:': 'P21',
    'death': 'P570',
    'birth': 'P569',
    'name': 'P1477',
    'honorific': 'P1035',
}


PROPERTY_RESOLVERS = {}
def resolver(*properties):
    """ Decorator to register a function as resolver for the given property.
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
        logger.debug("don't know how to resolve value %s of property %s" % (
            repr(value), property
        ))
        return None


@resolver('P509', 'P734', 'P742', 'P735', 'P1477')
def identity_resolver(property, value, language):
    """ Default resolver, converts to unicode and surrounds with double quotes """
    return '"%s"' % unicode(value).replace('"', '\\"') if value else None


@cache.cached
@resolver('P21')
def gender_resolver(property, value, language):
    """ Resolve gender """
    results = search(value, language)
    if results and results[0]['label'] in {'male', 'female'}:
        return results[0]['id']
    else:
        return   # cache, but do not serialize


@cache.cached
@resolver('P569', 'P570')
def date_resolver(property, value, language):
    """ Resolves dates """
    value = value.lower().replace('(circa)', '').replace('(probable)', '') \
                .replace('(presumed)', '').replace('c.', '').strip()
    if not value:
        return None
    try:
        res = datetime.parse(value)
        return format_date(res.get('year'), res.get('month'), res.get('day'))
    except ValueError:
        logger.debug('cannot parse date ' + value)
        return None


@cache.cached
@resolver('P26', 'P40', 'P1038')
def name_resolver(property, value, language):
    """  Resolves people names """
    name, _ = text.fix_name(value)
    results = search(name, language, label_exact=True)
    return results[0]['id'] if results else ''  # cache, but do not serialize


@cache.cached
@resolver('P108', 'P97', 'P106', 'P19', 'P20', 'P27')
def generic_search_resolver(property, value, language):
    """ Last-hope resolver, searches wikidata hoping to find something
        which exactly matches the given value
    """
    results = search(value, language, label_exact=True)
    return results[0]['id'] if results else None


@resolver('P1035')
def honorifics_resolver(property, value, language):
    if language != 'en':
        raise ValueError('only english honorifics are supported, sorry')

    return {
        'prof': 'Q121594',
        'dr': 'Q4618975',
        'phd': 'Q4618975',
        'bishop': 'Q611644',
        'arcibishop': 'Q611644',
        'st': 'Q43115',
        'hon': 'Q2746176',
        'rev': 'Q42603',
        'prof': 'Q121594',
        'miss': 'Q13359947',
        'mrs': 'Q313549',
        'mister': 'Q177053',
        'mr': 'Q177053',
        'sir': 'Q209690',
    }.get(value.strip().lower(), None)


def call_api(action, cache=True, **kwargs):
    """ Invoke the given method of wikidata APIs with the given parameters
    """
    kwargs['format'] = 'json'
    kwargs['action'] = action
    resp = io.get_and_cache(WIKIDATA_API_URL, use_cache=cache, params=kwargs)
    return json.loads(resp)


def search(term, language, label_exact=False):
    """ Uses the wikidata APIs to search for a term
        :param term: The term to look for
        :param language: Search in this language
        :param label_exact: If true, return only items whose label
        exactly matches (case insensitive) the search term
        :returns: list of results
    """
    term = term.strip().lower()
    results = call_api('wbsearchentities', search=term, language=language).get('search', [])
    if label_exact:
        results = [r for r in results if r.get('label', '').lower() == term]
    return results


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
        statement += '\tS854\t"%s"' % url

    return statement


def format_date(year, month, day):
    """ Formats a date according to Wikidata syntax. Assumes that the date is mostly
        correct. The allowed values of the parameters are shown in the following
        truth table

            y m d ok
            --------
            1 1 1  1
            1 1 0  1
            1 0 1  0
            1 0 0  1
            --------
            0 1 1  1
            0 1 0  0
            0 0 1  0
            0 0 0  0

        :param year: year of the date
        :param month: month of the date. Only positive values allowed
        :param day: day of the date. Only positive values allowed
    """
    if day:
        precision = 11
    elif month:
        precision = 10
    elif year is not None:
        precision = 9
    else:
        raise ValueError('empty date')

    if (month and day) or (year is not None and not day):
        year = int(year) if year is not None else 0
        month = int(month) if month else 1
        day = int(day) if day else 1

        if month > 0 and day > 0:
            return '%+012d-%02d-%02dT00:00:00Z/%d' % (year, month, day, precision)

    raise ValueError('don\'t know how to format')
