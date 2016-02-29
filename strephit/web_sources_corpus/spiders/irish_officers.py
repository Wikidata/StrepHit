# -*- coding: utf-8 -*-
from scrapy import Request
from scrapy import Spider
from strephit.commons import text
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class IrishOfficersSpider(Spider):
    name = "irish_officers"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/Chronicle_of_the_law_officers_of_Ireland',
    )

    def parse(self, response):
        for url in response.xpath(
                    './/a[starts-with(@title, "Chronicle of the law officers of Ireland/")]/@href'
                ).extract()[4:-1]:
            yield Request('https://en.wikisource.org' + url, self.parse_detail)
            
    def parse_detail(self, response):
        for each in response.xpath(
                    './/div[@id="headerContainer"]/following-sibling::div//p'
                ):
            yield WebSourcesCorpusItem(
                url=response.url,
                name=text.clean_extract(each, './span//text()'),
                bio=text.clean_extract(each, './/text()', sep=' '),
            )

    def refine_item(self, response, item):
        return super(IrishOfficersSpider, self).refine_item(response, item)
