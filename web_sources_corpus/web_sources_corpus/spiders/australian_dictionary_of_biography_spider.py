#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from scrapy import Request, Spider
from web_sources_corpus.items import WebSourcesCorpusItem


class AustralianDictionaryOfBiographySpider(Spider):
    """A spider for the Australian Dictionary of Biography website"""
    name = 'adb'
    allowed_domains = ['adb.anu.edu.au']
    start_urls = ['http://adb.anu.edu.au/biographies/name/']
    
    def parse(self, response):
        people_list = response.css('ol.searchListings li a')
        for person in people_list:
            link = person.xpath('@href').extract_first()
            url = response.urljoin(link)
            yield Request(url, self.parse_person)
        
        # Pagination handling: look for anchors with text = 'next'
        next_page = response.xpath("//a[.='next']")
        if next_page:
            # There should be 2 equal nodes (top + bottom of the page), so take the first
            url = response.urljoin(next_page.extract_first())
            yield Request(url, self.parse)
    
    
    def parse_person(self, response):
        item = WebSourcesCorpusItem()
        item['url'] = response.url
        item['name'] = response.css('h2::text').extract_first()
        item['bio'] = response.css('div.biographyContent').extract()
        yield item
        
