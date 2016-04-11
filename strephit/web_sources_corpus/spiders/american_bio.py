# -*- coding: utf-8 -*-
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class AmericanBioSpider(BaseSpider):
    name = "american_bio"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/Appletons%27_Cyclop%C3%A6dia_of_American_Biography',
    )

    list_page_selectors = 'xpath:.//div[@id="mw-content-text"]/table[2]//ul[1]/li/a/@href'
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]/table[1]//tr[3]//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name_from_title:clean:xpath:.//h1[@id="firstHeading"]//text()',
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]//p//text()',
    }

    def get_name_from_title(self, response, title):
        return title.split('/')[-1]
