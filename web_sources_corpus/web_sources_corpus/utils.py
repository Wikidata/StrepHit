import re


def clean_extract(sel, path, path_type='xpath', limit_from=None, limit_to=None, sep='\n'):
    if path_type == 'xpath':
        return clean(sep.join(x.strip()
            for x in sel.xpath(path).extract()[limit_from:limit_to]))
    elif path_type == 'css':
        return clean(sep.join(x.strip()
            for x in sel.css(path).extract()[limit_from:limit_to]))
    else:
        return None


def clean(s, unicode=True):
    flags = re.UNICODE if unicode else 0
    return re.subn(r'(\s){2,}', '\g<1>', s, flags)[0].strip()


def split_at(content, delimiters):
    """ Splits content using given delimiters following their order, for example

    >>> [x for x in split_at(range(11), range(3,10,3))]
    [(None, [1, 2]), (3, [4, 5]), (6, [7, 8]), (None, [9, 10])]

    :param content:
    :param delimiters:
    :return:
    """
    found = last = 0
    for i, x in enumerate(content):
        if x == delimiters[found]:
            yield (delimiters[found - 1] if found > 0 else None), content[last+1:i]
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
    :return: tuple `(birth_year, death_year)`, both strings as appearing in the
    original string. If the string cannot be parsed `(None, None)` is returned.
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
        match = re.findall(r'(ca?\.)?(\d+)-(ca?\.)?(\d*)', string)
        birth = death = None
        if match:
            birth = match[0][1] or None
            death = match[0][3] or None
    return birth, death
