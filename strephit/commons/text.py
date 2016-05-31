import re


def clean_extract(sel, path, path_type='xpath', limit_from=None, limit_to=None, sep='\n',
                  unicode=True):
    if path_type == 'xpath':
        return clean(sep.join(x.strip()
                              for x in sel.xpath(path).extract()[limit_from:limit_to]),
                     unicode=unicode)
    elif path_type == 'css':
        return clean(sep.join(x.strip()
                              for x in sel.css(path).extract()[limit_from:limit_to]),
                     unicode=unicode)
    else:
        return None


def clean(s, unicode=True):
    flags = re.UNICODE if unicode else 0
    return re.subn(r'(\s){2,}', '\g<1>', s, flags)[0].strip()


def split_at(content, delimiters):
    """ Splits content using given delimiters following their order, for example

    >>> [x for x in split_at(range(11), range(3,10,3))]
    [(None, [1, 2]), (3, [4, 5]), (6, [7, 8]), (None, [9, 10])]
    """
    found = last = 0
    for i, x in enumerate(content):
        if x == delimiters[found]:
            yield (delimiters[found - 1] if found > 0 else None), content[last + 1:i]
            last = i
            found += 1
            if found == len(delimiters):
                break
    if last < len(content):
        yield None, content[last:]


def parse_birth_death(string):
    """
    Parses birth and death dates from a string.

    :param string: String with the dates. Can be 'd. <year>' to indicate the
                   year of death, 'b. <year>' to indicate the year of birth, <year>-<year>
                   to indicate both birth and death year. Can optionally include 'c.' or 'ca.'
                   before years to indicate approximation (ignored by the return value).
                   If only the century is specified, birth is the first year of the century and
                   death is the last one, e.g. '19th century' will be parsed as `('1801', '1900')`
    :return: tuple `(birth_year, death_year)`, both strings as appearing in the original string.
             If the string cannot be parsed `(None, None)` is returned.
    """

    string = string.lower().replace(' ', '')
    if type(string) == unicode:
        # \u2013 is another fancy unicode character ('EN DASH') for '-'
        string = string.replace(u'\u2013', '-')

    if string.startswith('d.'):
        birth, death = None, re.findall(r'(ca?\.)?(\d+)', string)[0][1]
    elif string.startswith('b.'):
        birth, death = re.findall(r'(ca?\.)?(\d+)', string)[0][1], None
    elif 'century' in string:
        century = int(string[0:2])
        birth, death = '%d01' % (century - 1), '%d00' % century
    else:
        match = re.search(r'(ca?\.)?(?P<birth>\d+)-(ca?\.)?(?P<death>\d*)', string)
        birth = death = None
        if match:
            birth = match.group('birth') or None
            death = match.group('death') or None
    return birth, death


def extract_dict(response, keys_selector, values_selector, keys_extractor='.//text()',
                 values_extractor='.//text()', **kwargs):
    """ Extracts a dictionary given the selectors for the keys and the vaues.
    The selectors should point to the elements containing the text and not the
    text itself.

    :param response: The response object. The methods xpath or css are used
    :param keys_selector: Selector pointing to the elements containing the keys,
                          starting with the type `xpath:` or `css:` followed by
                          the selector itself
    :param values_selector: Selector pointing to the elements containing the values,
                            starting with the type `xpath:` or `css:` followed
                            by the selector itself
    :param keys_extracotr: Selector used to actually extract the value of the key from
                           each key element. xpath only
    :param keys_extracotr: Selector used to extract the actual value value from each
                           value element. xpath only
    :param \*\*kwargs: Other parameters to pass to `clean_extract`. Nothing good will
                       come by passing `path_type='css'`, you have been warned.
    """
    def get(selector):
        type, sel = selector.split(':', 1)
        if type == 'css':
            return response.css(sel)
        elif type == 'xpath':
            return response.xpath(sel)
        else:
            raise ValueError('Unknown selector type: ' + type)

    keys = get(keys_selector)
    values = get(values_selector)

    return dict(zip((clean_extract(k, keys_extractor, **kwargs) for k in keys),
                    (clean_extract(v, values_extractor, **kwargs) for v in values)))


def fix_name(name):
    """ tries to normalize a name so that it can be searched with the wikidata APIs

        :param name: The name to normalize
        :returns: a tuple with the normalized name and a list of honorifics
    """
    name = name.lower()

    try:
        last_name, first_name = name.split(',', 1)
        name = first_name.strip() + ' ' + last_name.strip()
    except ValueError:
        pass

    name = ''.join(c if c.isalnum() else ' '
                   for c in name if c.isalnum() or c.isspace())
    name, honorifics = strip_honorifics(name)

    return name.strip(), honorifics


def strip_honorifics(name):
    """ Removes honorifics from the name

        :param name: The name
        :returns: a tuple with the name without honorifics and a list of honorifics
    """
    honorifics = []
    changed = True
    while changed:
        changed = False
        for prefix in ['prof', 'dr', 'phd', 'sir', 'mr', 'mrs', 'miss', 'mister',
                       'bishop', 'arcibishop', 'st', 'hon', 'rev', 'prof']:
            if name.startswith(prefix):
                honorifics.append(prefix)
                changed = True
                name = name[len(prefix):]
                if name and name[0] == '.':
                    name = name[1:]
                name = name.strip()
    return name, honorifics
