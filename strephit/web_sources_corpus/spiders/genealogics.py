#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import logging
from lxml.html import fromstring
from scrapy import Request, Spider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem
from strephit.commons.text import clean_extract


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
        else:
            logging.debug("No next page link found: %s" % next_page)
    
    
    def parse_person(self, response):
        item = WebSourcesCorpusItem()
        item['url'] = response.url
        name = clean_extract(response, "//h1[contains(@class, 'header')]//text()")
        if name:
            item['name'] = name
        else:
            logging.debug("No name found for item with URL '%s'" % item['url'])
        bio_nodes = response.xpath("//li[contains(., 'BIOGRAPHY')]").extract()
        if bio_nodes:
            item['bio'] = fromstring('\n'.join(bio_nodes)).text_content().strip()
        else:
            logging.debug("No raw text biography found for %s" % item['name'])
        item['other'] = {}
        keys = response.css('li#info td.fieldnameback')
        if keys:
            for key_node in keys:
                key_text = key_node.xpath('.//text()').extract_first()
                # Take the first sibling of the key node as the value
                value = key_node.xpath('./following-sibling::td[1]')
                if value:
                    people_links = value.xpath(".//a[contains(@href, 'getperson')]")
                    if people_links:
                        logging.debug("Values with links found for key '%s'" % key_text)
                        item['other'][key_text] = []
                        for person in people_links:
                            name = person.xpath('.//text()').extract_first()
                            link = person.xpath('@href').extract_first()
                            item['other'][key_text].append({name: response.urljoin(link)})
                    else:
                        literal_value = clean_extract(value, './/text()')
                        item['other'][key_text] = literal_value
                else:
                    logging.debug("No value found for key '%s'" % key_text)
        else:
            logging.debug("No semi-structured data found for '%s'" % item['name'])
        yield item
