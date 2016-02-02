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


def clean(s):
    return re.subn(r'(\s){2,}', '\g<1>', s, re.UNICODE)[0].strip()


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
