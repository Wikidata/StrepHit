# -*- coding: utf-8 -*-
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class WhoIsWhoInChinaSpider(BaseSpider):
    name = "who_is_who_in_china"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/Who%27s_Who_in_China_(3rd_edition)',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]//table//a[not(@class="new")]/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:(.//p/b)[2]/text()',
        'bio': 'clean:xpath:.//div[@class="tiInherit"]/following-sibling::p//text()',
    }

    def refine_item(self, response, item):
        return super(WhoIsWhoInChinaSpider, self).refine_item(response, item)
