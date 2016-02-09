#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# TODO replace all prints with logger
import re
import click
import json
import os
import requests


def get_text(volume_url, cache=None):
    if cache and os.path.exists(cache):
        with open(cache) as f:
            content = f.read().decode('utf8')
    else:
        r = requests.get(volume_url)
        r.raise_for_status()
        content = r.text
        if cache:
            with open(cache, 'w') as f:
                f.write(content.encode('utf8'))
    return content


def parse_and_save(text, separator, out_file):
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
        cache = '/tmp/bio_dir_of_america_{volume}.txt'.format(volume=volume)
        volume_url = 'https://archive.org/download/biographicaldict{volume:02d}johnuoft/' \
                     'biographicaldict{volume:02d}johnuoft_djvu.txt'.format(volume=volume)
        vol = get_text(volume_url, cache if use_cache else None)
        parse_and_save(vol, ur'([A-Z]+, [A-Z][a-z]+ ?),[^,]+,', out_file)


@cli.command()
@click.pass_context
def who_was_who(ctx):
    out_file = ctx.obj.pop('out_file')
    use_cache = ctx.obj.pop('cache')

    cache = '/tmp/who_is_who.txt'
    url = 'https://archive.org/download/whowaswhocompani01londuoft/' \
          'whowaswhocompani01londuoft_djvu.txt'

    text = get_text(url, cache if use_cache else None)
    parse_and_save(text, ur'([A-Z]+, ([0-9A-Z][. \-a-z]+)+),[^,]+[,;]', out_file)
    

if __name__ == '__main__':
    cli(obj={})
