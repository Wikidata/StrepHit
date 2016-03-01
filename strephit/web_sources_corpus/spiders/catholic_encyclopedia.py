# -*- coding: utf-8 -*-
import scrapy
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class CatholicEncyclopediaSpider(BaseSpider):
    name = "catholic_encyclopedia"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/Catholic_Encyclopedia_%281913%29',
    )

    list_page_selectors = 'xpath:.//div[@id="mw-content-text"]/ul[1]//a/@href'
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]/table[1]//tr[4]//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name_from_title:clean:xpath:.//h1[@id="firstHeading"]//text()',
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]//p//text()',
    }

    def get_name_from_title(self, response, title):
        return title.split('/')[-1]
