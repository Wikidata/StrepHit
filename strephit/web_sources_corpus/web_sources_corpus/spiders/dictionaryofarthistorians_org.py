# -*- coding: utf-8 -*-
from scrapy import Request
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus.spiders import BaseSpider


class DictionaryofarthistoriansOrgSpider(BaseSpider):
    name = "dictionaryofarthistorians_org"
    allowed_domains = ["dictionaryofarthistorians.org"]

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@class="navigation-by-letter"]/following-sibling::p/a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
       'name': 'clean:xpath:.//h1[@class="arthist-publish-profile__name"]//text()',
        'birth': 'clean:xpath:.//div[@class="arthist-publish-profile__birthdate"]/p//text()',
        'death': 'clean:xpath:.//div[@class="arthist-publish-profile__deathdate"]/p//text()',
        'bio': 'clean:xpath:.//div[@class="arthist-publish-profile__body"]/p//text()',
    }

    def start_requests(self):
        for letter in 'abcdefghijklmnopqrstuvwxyz':
            yield Request('https://dictionaryofarthistorians.org/%s.html' % letter,
                          self.parse)
