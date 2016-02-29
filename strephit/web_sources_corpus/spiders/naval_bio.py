# -*- coding: utf-8 -*-
import scrapy
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class NavalBioSpider(BaseSpider):
    name = "naval_bio"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/A_Naval_Biographical_Dictionary',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]/ul[position()>4]//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name_from_title:clean:xpath:.//h1[@id="firstHeading"]//text()',
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]//p[position()>1]//text()',
    }

    def get_name_from_title(self, response, title):
        return title.split('/')[-1]
