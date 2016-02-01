# -*- coding: utf-8 -*-
import scrapy
import json
from scrapy import Request
from web_sources_corpus.items import WebSourcesCorpusItem


class NndbComSpider(scrapy.Spider):
    name = "nndb_com"
    start_urls = (
        'http://www.nndb.com/',
    )

    def parse(self, response):
        for url in response.css('.newslink').xpath('@href').extract():
            yield Request(url, self.parse_letter)

    def parse_letter(self, response):
        for url in response.xpath(
                './/a[contains(@href, "http://www.nndb.com/people/")]/@href'
        ).extract():
            yield Request(url, self.parse_person)

    def parse_person(self, response):
        base = './/table//td[1]//table//tr[3]//table//td'

        data = {}
        for paragraph in response.xpath(base + '//p'):
            fields = paragraph.xpath('./b/text()').extract()
            if not fields:
                continue

            contents = paragraph.xpath('.//text()').extract()
            for field, values in self.split_at(contents, fields):
                if field is not None:
                    data[field.lower().strip().replace(':', '')] = ' '.join(values).strip()

        return WebSourcesCorpusItem(
            name=response.xpath(base + '//b[1]/text()').extract()[0],
            url=response.url,
            birth=data.get('born'),
            death=data.get('died'),
            other=json.dumps(data)
        )

    def split_at(self, content, delimiters):
        found = last = 0
        for i, x in enumerate(content):
            if x == delimiters[found]:
                yield (delimiters[found - 1] if found > 0 else None), content[last+1:i]
                last = i
                found += 1
                if found == len(delimiters):
                    break
        if last < len(content):
            yield None, content[last:]
