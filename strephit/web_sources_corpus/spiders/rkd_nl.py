#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import logging
from strephit.commons.text import clean_extract
from strephit.web_sources_corpus.items import WebSourcesCorpusItem
from strephit.web_sources_corpus.spiders.BaseSpider import BaseSpider


class RKDArtistsSpider(BaseSpider):
    """A spider for RKD Netherlands Institute for Art History website"""
    name = 'rkd_nl'
    allowed_domains = ['rkd.nl']
    start_urls = ['https://rkd.nl/en/explore/artists']
    
    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@class="header"]/a/@href'
    next_page_selectors = 'xpath:.//a[@title="Next page"]/@href'
    
    item_class = WebSourcesCorpusItem
    # There seems to be semi-structured data only here
    item_fields = {
        'name': 'clean:xpath:.//h2/text()'
    }

    def extract_dl_key_value(self, dl_pairs, item):
        """ Feed the item with key-value pairs extracted from <dl> tags """
        for pair in dl_pairs:
            key = pair.xpath('./dt/text()').extract_first().replace(' ', '_').lower()
            value = clean_extract(pair, './dd//text()')
            if key or value:
                item['other'][key] = value
            else:
                logging.debug("Couldn't extract key or value from pair node '%s'" % pair)
        return item

    def refine_item(self, response, item):
        item['other'] = {}
        name = item['name']
        # Alias
        alias = clean_extract(response, './/div[@class="expandable-header"][contains(., "Name variations")]/following-sibling::div[@class="expandable-content"]//dd/text()')
        if alias:
            item['other']['alias'] = alias
        else:
            logging.debug("No alias found for '%s'" % name)
        # Relevant left key-value pairs
        left = response.xpath('..//div[@class="left"]/div[@class="fieldGroup"]/dl')
        if left:
            item = self.extract_dl_key_value(left, item)
        else:
            logging.debug("No relevant key-value pairs found on the left box for '%s'" % name)
        # Relevant right key-value pairs
        right = response.xpath('.//div[@class="right"]/div[@class="fieldGroup split"]/dl')
        if right:
            item = self.extract_dl_key_value(right, item)
        else:
            logging.debug("No relevant key-value pairs found on the right box for '%s'" % name)
        return super(RKDArtistsSpider, self).refine_item(response, item)
