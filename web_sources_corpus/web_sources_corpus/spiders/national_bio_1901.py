# -*- coding: utf-8 -*-
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem


class NationalBio1901Spider(BaseSpider):
    name = "national_bio_1901"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/Dictionary_of_National_Biography,_1901_supplement,_Volume_1',
        'https://en.wikisource.org/wiki/Dictionary_of_National_Biography,_1901_supplement,_Volume_2',
        'https://en.wikisource.org/wiki/Dictionary_of_National_Biography,_1901_supplement,_Volume_3',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//table[@class="prettytable"]//tr[4]//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name_from_title:clean:xpath:.//h1[@id="firstHeading"]/text()',
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]//p//text()',
    }

    def refine_item(self, response, item):
        return super(NationalBio1901Spider, self).refine_item(response, item)

    def get_name_from_title(self, response, title):
        return ''.join(title.split('(')[:-1]).strip()
