# -*- coding: utf-8 -*-
from scrapy import Spider, Request

from strephit.web_sources_corpus.items import WebSourcesCorpusItem
from strephit.commons import text


class ModernEnglishBioSpider(Spider):
    name = "modern_english_bio"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/Modern_English_Biography',
    )

    def parse(self, response):
        for url in response.xpath(
            './/a[starts-with(@title, "Modern English Biography/")]/@href'
        ).extract():
            yield Request('https://en.wikisource.org' + url, self.parse_detail)

    def parse_detail(self, response):
        for each in response.xpath(
            './/div[@id="headerContainer"]/following-sibling::p'
        ):
            item = WebSourcesCorpusItem(
                url=response.url,
                bio=text.clean_extract(each, './/text()', sep=' '),
            )

            if each.xpath('./a'):
                item['name'] = text.clean_extract(each, './a[1]//text()')

            if 'name' in item or item['bio']:
                yield item
