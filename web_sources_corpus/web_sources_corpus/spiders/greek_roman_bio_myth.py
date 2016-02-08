# -*- coding: utf-8 -*-
import scrapy
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
        return item if len(item['bio']) > 50 else None
