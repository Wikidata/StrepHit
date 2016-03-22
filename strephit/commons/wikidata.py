from __future__ import absolute_import
import json
import logging
import itertools
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
                logger.error('multiple resolvers registered for property %s, '
                             'only the last one will be kept' % property)
            PROPERTY_RESOLVERS[property] = function
        return function
    return decorator


def resolve(property, value, language, **kwargs):
    """ Tries to resolve the Wikidata ID of an object given its string representation
        :param property: Wikidata ID of the property to resolve
        :param value: String value
        :param language: Search only this language
        :param kwargs: Additional info that might be useful to help the resolver
    """
    if property in PROPERTY_RESOLVERS:
        return PROPERTY_RESOLVERS[property](property, value, language, **kwargs)
    else:
        logger.debug("don't know how to resolve value %s of property %s" % (
            repr(value), property
        ))
        return None


@resolver('P509', 'P734', 'P742', 'P735', 'P1477')
def identity_resolver(property, value, language, **kwargs):
    """ Default resolver, converts to unicode and surrounds with double quotes """
    return '"%s"' % unicode(value).replace('"', '\\"') if value else None


@cache.cached
@resolver('P21')
def gender_resolver(property, value, language, **kwargs):
    """ Resolve gender """
    results = search(value, language, type_=4369513)
    if results and results[0]['labels']['en']['value'] in {'male', 'female'}:
        return results[0]['id']
    else:
        return ''  # cache, but do not serialize


@cache.cached
@resolver('P569', 'P570')
def date_resolver(property, value, language, **kwargs):
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
def name_resolver(property, value, language, **kwargs):
    """ Resolves people names. Works better if generic biographic
        information, such as birth/death dates, is provided.
        :param kwargs: dictionary of wikidata property -> list of values
    """

    name, _ = text.fix_name(value)
    results = search(name, language, type_=5)  # Q5 = human

    def date_matches(their_dates, our_dates):
        """ Finds how many dates match between the ones we have and
            the ones they provide
        """
        matches = 0
        for theirs, ours in itertools.product(their_dates, our_dates):
            val = theirs['mainsnak']['datavalue']['value']
            their_date = parse_date(val['time'], val['precision'])
            our_date = parse_date(ours)
            matches += all(
                their_date[k] == our_date[k]
                for k in {'year', 'month', 'day'}
                if their_date.get(k) and our_date.get(k)  # consider precision
            )
        return matches

    # no additional info provided, return first match and pray
    if not kwargs:
        return results[0]['id'] if results else ''  # cache, but do not serialize

    # try to disambiguate using provided info
    logger.debug('disambiguating %d entities, searching for %s', len(results), value)
    most_matches = None
    known_properties = set(PROPERTY_TO_WIKIDATA.values())
    for entity in results:
        matches = 0
        for property, claim in entity['claims'].iteritems():
            try:
                if property == 'P569':
                    if 'P569' in kwargs:
                        matches += date_matches(claim, kwargs['P569'])

                elif property == 'P570':
                    if 'P570' in kwargs:
                        matches += date_matches(claim, kwargs['P570'])

                elif property in known_properties:
                    entity_val = set(filter(None, ('Q%d' % v['mainsnak']['datavalue']['value']['numeric-id']
                                                   for v in claim)))
                    our_val = set(filter(None, kwargs.get(property, [])))
                    weight = 0.5 if property == 'P21' else 1  # avoid matching only by gender
                    matches += len(our_val.intersection(entity_val)) * weight

            except (KeyError, TypeError):
                continue

        logger.debug('entity %s matched %d properties', entity['id'], matches)
        if most_matches is None or matches > most_matches[0]:
            most_matches = matches, entity

    if most_matches is None:
        return ''  # if no results
    else:
        if most_matches[0] >= 1:
            logger.debug('Resolved %s to %s', value, most_matches[1]['id'])
            return most_matches[1]['id']
        else:
            logger.debug('Could not resolve %s', value)
            return ''


@cache.cached
@resolver('P108', 'P97', 'P106', 'P27')
def generic_search_resolver(property, value, language, **kwargs):
    """ Last-hope resolver, searches wikidata hoping to find something
        which exactly matches the given value
    """
    results = search(value, language, type_=None)
    return results[0]['id'] if results else None


@resolver('P19', 'P20')
def place_resolver(property, value, language, **kwargs):
    """ Resolves place names
    """
    # Q515 = city, Q6526 = country
    results = search(value, language, type_={515, 6256})
    return results[0]['id'] if results else None


@resolver('P1035')
def honorifics_resolver(property, value, language, **kwargs):
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


def search(term, language, type_=None):
    """ Uses the wikidata APIs to search for a term. Can optionally specify a type
        (corresponding to the 'instance of' P31 wikidata property. If no type is
        specified simply returns all the items containing `term` in `label`
        :param term: The term to look for
        :param language: Search in this language
        :param type_: Type of the entity to look for, wikidata numeric id (i.e. without starting Q)
                      Can be int or anything iterable
        :returns: List of dicts with details (which details depend on `type_`)
    """
    term = term.strip().lower()
    results = call_api('wbsearchentities', search=term, language=language, limit='max').get('search', [])
    logger.debug('found %d entities with term "%s"', len(results), term)
    if type_:
        if not isinstance(type_, (list, set)):
            type_ = set([type_])
        else:
            type_ = set(type_)

        ids = '|'.join(r['id'] for r in results)
        details = call_api('wbgetentities', ids=ids, props='claims|labels')
        results = []
        for eid, entity in details.get('entities', {}).iteritems():
            entity_type = entity.get('claims', {}).get('P31', [])
            if any(t['mainsnak']['datavalue']['value']['numeric-id'] in type_ for t in entity_type):
                results.append(entity)
        logger.debug('refined search to %d entities of types %s', len(results), repr(type_))
    else:
        results = [r for r in results if r.get('label', '').lower() == term]
    return results


def finalize_statement(subject, property, value, language, url=None,
                       resolve_property=True, resolve_value=True, **kwargs):
    """ Given the components of a statement, convert it into a quick statement.
        :param subject: Subject of the statement (its Wikidata ID)
        :param property: Property of the statement
        :param value: Value of the statement (to be resolved)
        :param language: Language used to resolve the value
        :param url: Source of the statement (corresponds to S854)
        :param resolve_property: Whether `property` is already a Wikidata ID or needs
                                 to be resolved
        :param resolve_value: Whether `value` can be inserted into the statement as-is
                              or needs to be resolved
        :param kwargs: additional information used to resolve `value`
    """
    if resolve_property:
        property = PROPERTY_TO_WIKIDATA.get(property)

    if not property or value is None:
        return None

    if resolve_value:
        value = resolve(property, value.replace('\n', ' '), language, **kwargs)

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


def parse_date(date, precision=None):
    """ Tries to parse a date serialized according to the wikidata format
        into its components year, month and day
        :return: dict (year, month, day)
    """

    parts = date.split('/')
    if not precision:
        precision = int(parts[-1]) if len(parts) == 2 else 11
    date, time = parts[0].split('T')
    year, month, day = date[1:].split('-')  # the first char is year sign

    return {
        'year': int(date[0] + year),
        'month': int(month) if precision >= 10 else None,
        'day': int(day) if precision >= 11 else None,
    }
