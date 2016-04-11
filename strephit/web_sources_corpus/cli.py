# -*- encoding: utf-8 -*-
import os

import click
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from strephit.web_sources_corpus.preprocess_corpus import preprocess_corpus
from strephit.web_sources_corpus import run_all, archive_org


@click.command()
@click.argument('spider-name', nargs=-1, required=True)
@click.argument('results-dir', type=click.Path(resolve_path=True, file_okay=False))
def crawl(spider_name, results_dir):
    """ Run one or more spiders """
    settings = get_project_settings()
    # prevent scrapy from configuring its own logging, since we already have it
    settings.set('LOG_ENABLED', False)

    process = CrawlerProcess(settings)
    for s in spider_name:
        process.settings.set('FEED_URI',
                             'file://%s.jsonlines' % os.path.join(results_dir, s))
        process.settings.set('FEED_FORMAT', 'jsonlines')
        spider = process.spider_loader.load(s)
        process.crawl(spider)
    process.start()


CLI_COMMANDS = {
    'preprocess_corpus': preprocess_corpus,
    'run_all': run_all.main,
    'scrapy_crawl': crawl,
    'archive_org_crawl': archive_org.cli,
}


@click.group(name='web_sources_corpus', commands=CLI_COMMANDS)
@click.pass_context
def cli(ctx):
    """ Corpus retrieval from the web """
    pass
