#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import re
import click
import json
import os
import requests


def get_volume(number, use_cache=True):
    cached = '/tmp/bio_dir_of_america_{volume}.txt'.format(volume=number)
    if use_cache and os.path.exists(cached):
        with open(cached) as f:
            content = f.read().decode('utf8')
    else:
        volume_url = 'https://archive.org/download/biographicaldict{volume:02d}johnuoft/' \
                     'biographicaldict{volume:02d}johnuoft_djvu.txt'.format(volume=number)
        r = requests.get(volume_url)
        r.raise_for_status()
        content = r.text
        if use_cache:
            with open(cached, 'w') as f:
                f.write(content.encode('utf8'))
    return content


@click.command()
@click.argument('out-file', type=click.File('w'))
@click.option('--cache/--no-cache', default=True)
def main(out_file, cache):
    items = []
    current_item = None
    for volume in xrange(1, 11):
        print 'Volume', volume
        for line in get_volume(volume, use_cache=cache).split('\n'):
            if not line:
                continue
            match = re.match(ur'([A-Z]+, [A-Z][a-z]+ ?),[^,]+,', line)
            if match:
                if current_item:
                    items.append(current_item)
                print '%s' % match.group(1)
                current_item = {
                    'name': match.group(1),
                    'bio': '',
                }
            elif current_item:
                current_item['bio'] += line

    print 'Got {} items'.format(len(items))
    json.dump(items, out_file)


if __name__ == '__main__':
    main()
