# -*- coding: utf-8 -*-
import json
from scrapy import Request
from strephit.commons import text
from strephit.web_sources_corpus.spiders.BaseSpider import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class BbcCoUkSpider(BaseSpider):
    name = "bbc_co_uk"
    allowed_domains = ["www.bbc.co.uk"]

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//a[@class="artist"]/@href'
    next_page_selectors = 'xpath:.//div[@class="topPagination"]//li[@class="next"]//a/@href'

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//div[@id="info"]/h1/text()',
        'bio': 'clean:xpath:.//div[@id="info"]/div[@id="bio"]//text()',
        'other': {
            'short-desc': 'xpath:.//div[@id="info"]/ul[@id="short-desc"]/li//text()',
            'oup': 'clean:xpath:.//div[@id="info"]/div[@id="oup"]/p[1]/text()',
            'read-more': 'clean:xpath:.//div[@id="info"]//div[@id="read-more"]//text()',
            'how-to-cite': 'clean:xpath:.//div[@id="how-to-cite"]//text()',
        }
    }

    def start_requests(self):
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            yield Request(
                'http://www.bbc.co.uk/arts/yourpaintings/artists?letter=' + letter,
                self.parse)

    def refine_item(self, response, item):
        for each in item['other']['short-desc']:
            birth, death = text.parse_birth_death(each)
            if birth or death:
                item['birth'] = birth
                item['death'] = death

        item['bio'] += item['other'].pop('read-more')
        return super(BbcCoUkSpider, self).refine_item(response, item)
