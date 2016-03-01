# -*- coding: utf-8 -*-
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class ChineseBioSpider(BaseSpider):
    name = "chinese_bio"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/A_Chinese_Biographical_Dictionary',
    )

    list_page_selectors = None
    detail_page_selectors =  'xpath:.//div[@class="poem"]//a[not(@class="new")]/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath://div[@id="headerContainer"]/following-sibling::div[1]//p/b[1]/text()',
        'bio': 'clean:xpath:.//div[@id="headerContainer"]/following-sibling::div[1]//p//text()',
    }

    def refine_item(self, response, item):
        return super(ChineseBioSpider, self).refine_item(response, item)
