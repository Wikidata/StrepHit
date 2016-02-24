# -*- coding: utf-8 -*-
import scrapy
import logging
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem


class GreekRomanBioMythSpider(BaseSpider):
    name = "greek_roman_bio_myth"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/Dictionary_of_Greek_and_Roman_Biography_and_Mythology',
    )

    list_page_selectors = 'xpath:.//div[@id="mw-content-text"]/ul/li[position()>2]/a/@href'
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]/ul/li/a[not(@class="new")]/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name_from_title:clean:xpath:.//h1[@id="firstHeading"]/text()',
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]/p//text()',
    }

    def get_name_from_title(self, response, title):
        return title.split('/')[-1]

    def refine_item(self, response, item):
        if len(item['bio']) < 50:
            logging.debug('skipped %s, bio is too short! bio: %s' % (
                item['url'], item['bio']
            ))
            return None
        else:
            return super(GreekRomanBioMythSpider, self).refine_item(response, item)
