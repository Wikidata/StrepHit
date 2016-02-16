# -*- coding: utf-8 -*-
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem


class NationalBioSpider(BaseSpider):
    name = "national_bio"
    allowed_domains = ["en.wikisource.org"]

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//table[@class="prettytable"]//tr[4]//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name_from_title:clean:xpath:.//h1[@id="firstHeading"]/text()',
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]//p//text()',
    }

    def __init__(self, year):
        assert year in {'1901', '1912'}
        self.start_urls = (
            'https://en.wikisource.org/wiki/Dictionary_of_National_Biography,_%s_supplement,_Volume_1' % year,
            'https://en.wikisource.org/wiki/Dictionary_of_National_Biography,_%s_supplement,_Volume_2' % year,
            'https://en.wikisource.org/wiki/Dictionary_of_National_Biography,_%s_supplement,_Volume_3' % year
        )
        

    def get_name_from_title(self, response, title):
        return ''.join(title.split('(')[:-1]).strip()
