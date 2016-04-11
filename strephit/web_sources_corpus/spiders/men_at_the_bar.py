# -*- coding: utf-8 -*-
from scrapy import Request

from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class MenAtTheBarSpider(BaseSpider):
    name = "men_at_the_bar"
    allowed_domains = ["en.wikisource.org"]
    base_url = 'https://en.wikisource.org/wiki/Men-at-the-Bar/Names_'

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]//ul//a[not(@class="new")]/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name_from_title:clean:xpath:.//h1[@id="firstHeading"]//text()',
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]//p//text()',
    }

    def start_requests(self):
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            yield Request(self.base_url + letter, self.parse)

    def refine_item(self, response, item):
        return super(MenAtTheBarSpider, self).refine_item(response, item)

    def get_name_from_title(self, response, title):
        return title.split('/')[-1]
