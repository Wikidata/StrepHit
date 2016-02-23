# -*- coding: utf-8 -*-
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem


class WhoIsWhoAmericaSpider(BaseSpider):
    name = "who_is_who_america"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/Woman%27s_Who%27s_Who_of_America,_1914-15',
    )

    list_page_selectors = 'xpath:.//table[@class="headertemplate"]//tr[3]//a[not(@class="new")]/@href'
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]//ul//a[not(@class="new")]/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//div[@id="headerContainer"]/following-sibling::div//p/b/a/text()',
        'bio': 'clean:xpath:.//div[@id="headerContainer"]/following-sibling::div//p[2]//text()',
    }

    def refine_item(self, response, item):
        return super(WhoIsWhoAmericaSpider, self).refine_item(response, item)
