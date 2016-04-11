# -*- coding: utf-8 -*-
from scrapy import Request

from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class ChristianBioSpider(BaseSpider):
    name = "christian_bio"
    allowed_domains = ["en.wikisource.org"]
    base_url = 'https://en.wikisource.org/wiki/Dictionary_of_Christian_Biography_and' \
               '_Literature_to_the_End_of_the_Sixth_Century/'

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]/ul//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name_from_title:clean:xpath:.//h1[@id="firstHeading"]//text()',
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]//p//text()',
    }

    def start_requests(self):
        for letter in 'ABCDEFGHIJKLMNOPRSTUVWXYZ':
            yield Request(self.base_url + letter, self.parse)

    def get_name_from_title(self, response, title):
        return title.split('/')[-1]
