#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import re
from requests import get

# The book has 10 volumes 
VOLUMES = [n for n in xrange(1, 11)]
# Must be filled
URL_TEMPLATE = "https://archive.org/download/biographicaldict%02djohnuoft/biographicaldict%02djohnuoft_djvu.txt"

items = []

for volume in xrange(1, 11):
    r = get(URL_TEMPLATE % (volume, volume))
    volume_content = r.text
    start_person = False
    # Skip empty lines
    for line in volume_content.split('\n'):
        if not line:
            continue
        match = re.match(ur'([A-Z]+, [A-Z][a-z]+ ?),[^,]+,', line)
        if match:
            start_person = True
            item = {'name': match.group(1)}
            
        items.append(item)