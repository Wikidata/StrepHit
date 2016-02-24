# -*- coding: utf-8 -*-
import scrapy
import json
from scrapy import Request
from web_sources_corpus import utils
from web_sources_corpus.items import WebSourcesCorpusItem


class RoyalsocietyOrgSpider(scrapy.Spider):
    name = "royalsociety_org"
    allowed_domains = ["royalsociety.org"]
    start_urls = (
        'http://www.royalsociety.org/',
    )

    def start_requests(self):
        yield Request(
            'https://royalsociety.org/api/Fellows/Search', self.parse, method='POST',
            body='{"SearchType":"fellows","Sort":"date","StartIndex":0,"PageSize":2000}',
            headers={'Content-Type': 'application/json; charset=utf8'}
        )

    def parse(self, response):
        data = json.loads(response.body)
        for fellow in data['Results']:
            yield Request('https://royalsociety.org' + fellow['FellowProfileUrl'] + '/',
                          self.parse_fellow,
                          meta=fellow)

    def parse_fellow(self, response):
        yield WebSourcesCorpusItem(
            url=response.url,
            bio=utils.clean_extract(response, './/div[@class="expandableBio"]//text()'),
            other=json.dumps(response.meta)
        )
