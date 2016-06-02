#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from __future__ import absolute_import
import json
import logging
from itertools import product

from strephit.commons import cache, io, datetime, text

logger = logging.getLogger(__name__)

WIKIDATA_API_URL = 'https://www.wikidata.org/w/api.php'
PROPERTIES_NAMESPACE = 120
PROPERTY_TO_WIKIDATA = {
    'Died of:': 'P509',
    # 'Marriage': 'P26',
    'Last Name': 'P734',
    # 'Children': 'P40',
    # 'Place of death': 'P20',
    # 'Relatives': 'P1038',
    'Year died': 'P570',
    'alt. Names': 'P742',
    'Year born': 'P569',
    'Given Name': 'P735',
    # 'Worked for': 'P108',
    # 'title': 'P97',
    # 'lblProfession': 'P106',
    # 'lblNationality': 'P27',
    'gender': 'P21',
    'lblIdentifier': 'P742',
    # 'Place of origin:': 'P19',
    'Gender:': 'P21',
    'death': 'P570',
    'birth': 'P569',
    'name': 'P1559',
    'honorific': 'P1035',
    ### Genealogics ###
    'Born': 'P569',
    'Buried': 'P570',
    u'Children\xa0': 'P40',
    #'Christened',
    'Died': 'P570',
    #'Divorced': ,
    'Family': 'P1038',
    'Father': 'P22',
    'First name(s)': 'P735',
    'Gender': 'P21',
    'Honorific': 'P1035',
    'Honours': 'P166',
    'Lived In': 'P551',
    'Married': 'P26',
    'Mentioned': 'P1249',
    'Mother': 'P25',
    'Occupation': 'P106',
    'Other Titles': 'P1449'
    #u'Same\xa0Person\xa0Link'
}
PROPERTY_TO_WIKIDATA.update({'Family %d' % i: 'P1038' for i in xrange(1, 21)})

PROPERTY_RESOLVERS = {}


def resolver(*properties):
    """ Decorator to register a function as resolver for the given properties.
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


@resolver('P509', 'P734', 'P742', 'P735', 'P1559')
def identity_resolver(property, value, language, **kwargs):
    """ Default resolver, converts to unicode and surrounds with double quotes """
    return '%s:"%s"' % (language, unicode(value).replace('"', '\\"')) if value else None


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
        return ''
    try:
        res = datetime.parse(value)
        return format_date(res.get('year'), res.get('month'), res.get('day'))
    except ValueError:
        logger.debug('cannot parse date ' + value)
        return ''


#@resolver('P26', 'P40', 'P1038')
def resolver_with_hints(property, value, language, **kwargs):
    """ Resolves people names. Works better if generic biographic
        information, such as birth/death dates, is provided.

        :param kwargs: dictionary of wikidata property -> list of values
    """

    type_ = {'type_': kwargs.pop('type_')} if 'type_' in kwargs else {}
    results = search(value, language, label_exact=False, **type_)

    def date_matches(their_dates, our_dates):
        """ Finds how many dates match between the ones we have and
            the ones they provide
        """
        matches = 0
        for theirs, ours in product(their_dates, our_dates):
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
    known_properties = set(PROPERTY_TO_WIKIDATA.values()) | set(kwargs)
    for entity in results:
        # for disambiguation pages
        if 'claims' not in entity:
            continue

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
                    m = len(our_val.intersection(entity_val))
                    matches += m * weight

                    logger.debug('property %s of entity %s is "%s" while provided value is "%s", '
                                 'match is %d', property, entity['id'], entity_val,
                                 our_val, m)

            except (KeyError, TypeError):
                continue

        logger.debug('entity %s matched %d properties', entity['id'], matches)
        if most_matches is None or matches > most_matches[0]:
            most_matches = matches, entity

    if most_matches is None:
        logger.debug('failed to resolve "%s"; no entity matches', value)
        return ''  # if no results
    else:
        if most_matches[0] >= 1:
            logger.debug('Resolved %s to %s', value, most_matches[1]['id'])
            return most_matches[1]['id']
        else:
            logger.debug('Could not resolve %s', value)
            return ''


@cache.cached
# @resolver('P108', 'P97', 'P106', 'P27', 'P166')
def generic_search_resolver(property, value, language, **kwargs):
    """ Last-hope resolver, searches wikidata hoping to find something
        which exactly matches the given value
    """
    results = search(value, language, type_=None)
    return results[0]['id'] if results else ''


@cache.cached
# @resolver('P19', 'P20')
def place_resolver(property, value, language, **kwargs):
    """ Resolves place names
    """
    # Q515 = city, Q6526 = country
    results = search(value, language, type_={515, 6256})
    return results[0]['id'] if results else ''


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
    }.get(value.strip().lower(), '')


def call_api(action, cache=True, **kwargs):
    """ Invoke the given method of wikidata APIs with the given parameters
    """
    kwargs['format'] = 'json'
    kwargs['action'] = action
    resp = io.get_and_cache(WIKIDATA_API_URL, use_cache=cache, params=kwargs)
    return json.loads(resp)


def search(term, language, type_=None, label_exact=True):
    """ Uses the wikidata APIs to search for a term. Can optionally specify a type
        (corresponding to the 'instance of' P31 wikidata property. If no type is
        specified simply returns all the items containing `term` in `label`

        :param term: The term to look for
        :param language: Search in this language
        :param type_: Type of the entity to look for, wikidata numeric id (i.e. without starting Q)
                      Can be int or anything iterable
        :param label_exact: Filter entities whose labels matches exactly the search term
        :returns: List of dicts with details (which details depend on `type_`)
    """
    term = term.strip().lower()
    results = call_api('wbsearchentities', search=term, language=language, limit='max').get('search', [])
    logger.debug('found %d entities with term "%s"', len(results), term)

    titles = call_api('query', list='search', srsearch=term, srlimit='50').get('query', {}).get('search', [])
    logger.debug('found %d pages with term "%s"', len(titles), term)

    for each in titles:
        title = each['title']
        entities = call_api('wbsearchentities', search=title, language=language, limit='max').get('search', [])
        results.extend(entities)

    logger.debug('obtained %d entities for "%s"', len(results), term)
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
        if type_ and not any(t['mainsnak']['datavalue']['value']['numeric-id'] in type_ for t in entity_type):
            continue
        elif label_exact:
            if 'label' in entity and entity['label'].lower() != term:
                continue
            elif 'labels' in entity and entity['labels'][language]['value'].lower().encode('utf8') != term:
                continue

        results.append(entity)

    msg = 'refined search to %d entities' % len(results)
    if type_:
        msg += ' of types %s' % repr(type_)
    if label_exact:
        msg += ' of label exact "%s"' % term
    logger.debug(msg)

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

    statement = u'%s\t%s\t%s' % (subject, property, value)
    if url:
        statement += u'\tS854\t"%s"' % url

    return statement


def format_date(year=None, month=None, day=None):
    """ Formats a date according to Wikidata syntax. Assumes that the date is mostly
        correct. The allowed values of the parameters are shown in the following
        truth table

        ==== ===== === ==
        year month day ok
        ==== ===== === ==
        1    1     1   1
        1    1     0   1
        1    0     1   0
        1    0     0   1
        0    1     1   1
        0    1     0   0
        0    0     1   0
        0    0     0   0
        ==== ===== === ==

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


def get_property_ids(batch):
    """
     Get the full list of Wikidata property IDs (pids).

     :param int batch: number of pids per call, to serve as paging for the API.
     :return: list of all pids
     :rtype: list
    """
    pids = []
    params = {
        'list': 'allpages',
        'apnamespace': PROPERTIES_NAMESPACE,
        'aplimit': batch,
    }
    # Paging mechanism
    logger.info("About to call the Wikidata API for property IDs, with paging ...")
    while True:
        r = call_api('query', **params)
        pid_batch = r['query']['allpages']
        pids.extend(pid_batch)
        if not r.get('continue'):
            logger.debug("Got all the property IDs")
            break
        else:
            next_call = r['continue']['apcontinue']
            logger.debug("Next API call will start from '%s' ..." % next_call)
            params['apfrom'] = next_call
    # Return 'P69', not 'Property:P69'
    logger.info("Total property IDs: %d" % len(pids))
    return [p['title'].split(':')[1] for p in pids]


def get_entities(ids, batch):
    """
     Retrieve Wikidata entities metadata.

     :param list ids: list of Wikidata entity IDs
     :param int batch: number of IDs per call, to serve as paging for the API.
     :return: dict of Wikidata entities with metadata
     :rtype: dict
    """
    entities = []
    batches = [ids[i:i + batch] for i in xrange(0, len(ids), batch)]
    # Paging mechanism
    logger.info("About to call the Wikidata API for entity metadata, with paging ...")
    logger.debug("Number of batches: %d" % len(batches))
    for i, ids_batch in enumerate(batches):
        r = call_api('wbgetentities', ids='|'.join(ids_batch))
        entity_batch = r['entities'].values()
        # properties.extend(r['entities'].viewvalues())
        entities.extend(entity_batch)
        entities_left = len(ids) - (i + 1) * batch
        if i % 10 == 0 and entities_left > 0:
            logger.debug('%d entities left' % entities_left)

    logger.info("Total entities: %d" % len(entities))
    return entities


def get_labels_and_aliases(entities, language_code):
    """
     Extract language-specific label and aliases from a list of Wikidata entities metadata.

     :param list entities: list of Wikidata entities with metadata.
     :param str language_code: 2-letter language code, e.g., `en` for English
     :return: dict of entities, with label and aliases only
     :rtype: dict
    """
    clean = {}
    for entity in entities:
        entity_id = entity['id']
        # Labels extraction
        labels = entity.get('labels')
        if not labels:
            logger.debug("No labels at all for entity ID '%s'. Skipping ..." % entity_id)
            continue
        language_specific_label = labels.get(language_code)
        if not language_specific_label:
            logger.debug("No '%s' labels for entity ID '%s'. Skipping ..." % (language_code, entity_id))
            continue
        clean[entity_id] = {}
        clean[entity_id]['label'] = language_specific_label['value']
        # Aliases extraction
        aliases = entity.get('aliases')
        if not aliases:
            logger.debug("No aliases at all for entity ID '%s'. Skipping ..." % entity_id)
        language_specific_aliases = aliases.get(language_code)
        if language_specific_aliases:
            clean[entity_id]['aliases'] = [alias['value'] for alias in language_specific_aliases]
        else:
            logger.debug("No '%s' aliases for entity ID '%s'. Skipping ..." % (language_code, entity_id))
    logger.info("Total entities with label and aliases: %d" % len(clean))
    return clean
