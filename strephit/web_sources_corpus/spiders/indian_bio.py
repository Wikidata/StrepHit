# -*- coding: utf-8 -*-
import scrapy
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class IndianBioSpider(BaseSpider):
    name = "indian_bio"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/The_Indian_Biographical_Dictionary_(1915)',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]/ul[position()>4]//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name_from_title:clean:xpath:.//h1[@id="firstHeading"]//text()',
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]//p//text()',
    }

    def get_name_from_title(self, response, title):
        return title.split('/')[-1]

    def refine_item(self, response, item):
        if 'appendix' in item['name'].lower():
            return None
        else:
            return super(IndianBioSpider, self).refine_item(response, item)
