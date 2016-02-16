# -*- coding: utf-8 -*-
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem


class AustralasianBioSpider(BaseSpider):
    name = "australasian_bio"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/The_Dictionary_of_Australasian_Biography',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]//table//tr[2]//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name_from_title:clean:xpath:.//h1[@id="firstHeading"]//text()',
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]//p//text()',
    }

    def refine_item(self, response, item):
        return super(AustralasianBioSpider, self).refine_item(response, item)

    def get_name_from_title(self, response, title):
        return title.split('/')[-1]
