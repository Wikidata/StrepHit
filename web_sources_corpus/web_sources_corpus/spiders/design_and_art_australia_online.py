#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from lxml.html import fromstring
from scrapy import Request, Spider
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus.utils import clean


class DesignAndArtAustraliaOnlineSpider(Spider):
    """A spider for the Design & Art Australia Online website"""
    name = 'daao'
    allowed_domains = ['www.daao.org.au']
    start_urls = ['https://www.daao.org.au/search/?q&selected_facets=record_type_exact%3APerson&page=1&advanced=false&view=view_list&results_per_page=100']
    
    def parse(self, response):
        people_list = response.css('div.text a')
        for person in people_list:
            link = person.xpath('@href').extract_first()
            url = response.urljoin(link)
            yield Request(url, self.parse_person)
        
        # Pagination handling
        next_page = response.css('a.pagination_right')
        if next_page:
            url = response.urljoin(next_page.xpath('@href').extract_first())
            yield Request(url, self.parse)
        
    
    def parse_person(self, response):
        item = WebSourcesCorpusItem()
        item['url'] = response.url
        item['name'] = response.css('span.name::text').extract_first().strip()
        item['bio'] = []
        item['bio'].append(clean(fromstring('\n'.join(response.css('div.description').extract())).text_content()))
        # There is some semi-structured data available in key-value pairs, as <dt> and <dd> tags
        semi_structured = response.css('div#tab_content_artist_summary')
        keys = filter(None, [k.strip() for k in semi_structured.xpath('//dt//text()').extract()])
        values = filter(None, [v.strip() for v in semi_structured.xpath('//dd//text()').extract()])
        # Build a dict by mapping keys to values, filtering out None values
        item['other'] = map(lambda x,y: {x:y}, keys, values)
        request = Request(item['url'] + 'biography', self.parse_bio)
        request.meta['item'] = item
        yield request

    
    def parse_bio(self, response):
        item = response.meta['item']
        item['bio'].append(fromstring('\n'.join(response.css('div.ui-accordion-content > p').extract())).text_content())
        yield item