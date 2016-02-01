# -*- coding: utf-8 -*-
import scrapy
from scrapy import Request
from web_sources_corpus import utils
from web_sources_corpus.items import WebSourcesCorpusItem


class CooperhewittOrgSpider(scrapy.Spider):
    name = "cooperhewitt_org"
    allowed_domains = ["collection.cooperhewitt.org"]
    start_urls = (
        'http://collection.cooperhewitt.org/people/page1',
    )

    def parse(self, response):
        for url in response.xpath(
                './/div[@class="row"]/div[2]/ul[@class="list-o-things"]//h1/a/@href'
        ).extract():
            yield Request(url + 'bio', self.parse_person)

        next = response.xpath('.//ul[@class="pagination"]/li[last()]/a/@href').extract()
        if next:
            yield Request('http://collection.cooperhewitt.org/people/' + next[0],
                          self.parse)

    def parse_person(self, response):
        name = utils.clean_extract(response.css('.page-header > h1 > a'))
        text = utils.clean_extract(response.css('.person-bio > p'))
        if text:
            yield WebSourcesCorpusItem(
                name=name,
                bio=text,
            )
