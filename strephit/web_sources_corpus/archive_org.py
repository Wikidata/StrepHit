#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import re
import click
import json
import os
import requests
from strephit.commons.io import get_and_cache


def parse_and_save(text, separator, out_file, url):
    current_item = None
    for line in text.split('\n'):
        if not line:
            continue
        match = re.match(separator, line)
        if match:
            if current_item:
                json.dump(current_item, out_file)
                out_file.write('\n')

            print '%s' % match.group(1)
            current_item = {
                'url': url,
                'name': match.group(1),
                'bio': '',
            }
        elif current_item:
            current_item['bio'] += line


@click.group()
@click.argument('out-file', type=click.File('w'))
@click.option('--cache/--no-cache', default=True)
@click.pass_context
def cli(ctx, out_file, cache):
    ctx.obj['out_file'] = out_file
    ctx.obj['cache'] = cache


@cli.command()
@click.pass_context
def american_bio(ctx):
    out_file = ctx.obj.pop('out_file')
    use_cache = ctx.obj.pop('cache')

    for volume in xrange(1, 11):
        print 'Volume', volume
        volume_url = 'https://archive.org/download/biographicaldict{volume:02d}johnuoft/' \
                     'biographicaldict{volume:02d}johnuoft_djvu.txt'.format(volume=volume)
        vol = get_and_cache(volume_url, use_cache)
        parse_and_save(vol, ur'([A-Z]+, [A-Z][a-z]+ ?),[^,]+,', out_file, volume_url)


@cli.command()
@click.pass_context
def who_was_who(ctx):
    out_file = ctx.obj.pop('out_file')
    use_cache = ctx.obj.pop('cache')

    url = 'https://archive.org/download/whowaswhocompani01londuoft/' \
          'whowaswhocompani01londuoft_djvu.txt'
    text = get_and_cache(url, use_cache)
    parse_and_save(text, ur'([A-Z]+, ([0-9A-Z][. \-a-z]+)+),[^,]+[,;]', out_file, url)
