#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import re

from lxml.html import fromstring
from scrapy import Request, Spider

from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class AustralianDictionaryOfBiographySpider(Spider):
    """A spider for the Australian Dictionary of Biography website"""
    name = 'australian_dictionary_of_biography'
    allowed_domains = ['adb.anu.edu.au']
    start_urls = ['http://adb.anu.edu.au/biographies/name/']

    def parse(self, response):
        people_list = response.css('ol.searchListings li a')
        for person in people_list:
            link = person.xpath('@href').extract_first()
            url = response.urljoin(link)
            yield Request(url, self.parse_person)

        # Pagination handling: look for anchors with text = 'next'
        next_page = response.xpath("//a[.='next']/@href")
        if next_page:
            # There should be 2 equal nodes (top + bottom of the page), so take the first
            url = response.urljoin(next_page.extract_first())
            yield Request(url, self.parse)

    def parse_person(self, response):
        item = WebSourcesCorpusItem()
        item['url'] = response.url
        name_and_dates = response.css('h2::text').extract_first()
        dates = re.search(r'\((\d{4})[^\d](\d{4})\)', name_and_dates, re.UNICODE)
        item['name'] = re.search(r'[^\d]+', name_and_dates, re.UNICODE).group().strip(' (')
        if dates:
            item['birth'] = dates.group(1)
            item['death'] = dates.group(2)
        item['bio'] = fromstring(response.css('div.biographyContent').extract_first()).text_content().strip()
        yield item
