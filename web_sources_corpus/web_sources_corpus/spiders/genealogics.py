#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import logging

from lxml.html import fromstring
from scrapy import Request, Spider
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus.utils import clean_extract

class GenealogicsSpider(Spider):
    """A spider for Leo's Genealogics website"""
    name = 'genealogics'
    allowed_domains = ['www.genealogics.org']
    start_urls = ['http://www.genealogics.org/search.php?mybool=AND&nr=200']
    
    
    def parse(self, response):
        people_list = response.css('a.pers')
        for person in people_list:
            link = person.xpath('@href').extract_first()
            url = response.urljoin(link)
            yield Request(url, self.parse_person)
        
        # Pagination handling
        next_page = response.xpath("//a[@title='Next']/@href").extract_first()
        if next_page:
            url = response.urljoin(next_page)
            yield Request(url, self.parse)
    
    
    def parse_person(self, response):
        item = WebSourcesCorpusItem()
        item['url'] = response.url
        item['name'] = clean_extract(response, 'h1#nameheader::text', path_type='css')
        bio_nodes = response.xpath("//li[contains(., 'BIOGRAPHY')]").extract()
        if bio_nodes:
            item['bio'] = fromstring('\n'.join(bio_nodes)).text_content().strip()
        else:
            logging.debug("No raw text biography found for %s" % item['name'])
        item = {}
        item['other'] = {}
        for key_node in response.css('li#info td.fieldnameback'):
            key = key_node.xpath('.//text()').extract_first()
            # Take the first sibling of the key node as the value
            value = key_node.xpath('./following-sibling::td[1]').xpath('.//text()').extract_first()
            item['other'][key] = value