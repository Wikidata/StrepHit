# -*- coding: utf-8 -*-
import scrapy
import json
import re
from scrapy import Request
from web_sources_corpus import utils
from web_sources_corpus.items import WebSourcesCorpusItem


class GameoOrgSpider(scrapy.Spider):
    name = "gameo_org"
    allowed_domains = ["gameo.org"]
    start_urls = (
        'http://gameo.org/index.php?title=Special:AllPages&from='
        '108+Chapel+%28100+Mile+House%2C+British+Columbia%2C+Canada%29',
    )

    def parse(self, response):
        for link in response.xpath('.//table[@class="mw-allpages-table-chunk"]//a'):
            title = link.xpath('./text()').extract()[0]
            match = re.match(r'^([^(]+) \(([^)]+)\)$', title)
            if match:
                details = match.group(2)
                if (re.match(r'\d{,4}-\d{,4}', details) or
                        re.match(r'\d{,2}(th|st|nd|rd) century', details) or
                        re.match(r'd\. \d{,4}', details) or
                        re.match(r'b\. \d{,4}', details)):
                    yield Request('http://gameo.org' + link.xpath('@href').extract()[0],
                                  self.parse_detail)

        next = response.xpath('.//td[@class="mw-allpages-nav"]/a[3]')
        if next:
            yield Request('http://gameo.org' + next.xpath('@href').extract()[0],
                          self.parse)

    def parse_detail(self, response):
        title = utils.clean_extract(response.selector, './/h1[@id="firstHeading"]//text()')
        name, birth, death = self.parse_title(title)

        return WebSourcesCorpusItem(
            name=name,
            birth=birth,
            death=death,
            url=response.url,
            bio=self.extract_bio(response.selector),
        )

    def parse_title(self, title):
        name, info = title.split('(')
        if info.startswith('d.'):
            birth, death = None, re.findall(r'\d+', info)[0]
        elif info.startswith('b.'):
            birth, death = re.findall(r'\d+', info)[0], None
        elif 'century' in info:
            birth, death = None, None
        else:
            birth, death = re.findall(r'(\d+)-(\d+)', info)[0]
        return name.strip(), birth, death

    def extract_bio(self, sel):
        bio = utils.clean_extract(
            sel,
            './/div[@id="mw-content-text"]/h1[1]/preceding-sibling::*//text()',
        )

        assert bio
        return bio
