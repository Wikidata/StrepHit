from dateutil import parser
import re


def parse(string):
    """ Try to parse a date expressed in natural language.
        :return: dictionary with year, month, day
    """
    class CustomDatetime:
        """ Hackish way to extract extract day, month and year only when
            they were defined in the original string
        """
        result = {}

        def replace(self, **kwargs):
            self.result.update(kwargs)

    parsed = CustomDatetime()
    try:
        _ = parser.parse(string, default=parsed)
    except ValueError:
        pass

    if parsed.result:
        return parsed.result
    else:
        return _fallback(string)


_custom_patterns = map(
    lambda (pattern, transform): (re.compile(pattern, re.UNICODE | re.IGNORECASE),
                                  transform), [
        (r'b\.c\. (?P<y>\d+)', lambda match: {'year': int('-' + match.group('y'))}),
        (r'(?P<y>\d+)\s*bc', lambda match: {'year': int('-' + match.group('y'))}),
    ]
)


def _fallback(string):
    """ Try to parse the string even when dateutil fails """
    result = {'year': None, 'month': None, 'day': None}
    for regex, transform in _custom_patterns:
        match = regex.match(string)
        if match:
            result.update(transform(match))
            break
    return result
