# -*- coding: utf-8 -*-
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem


class MenOfTimeSpider(BaseSpider):
    name = "men_of_time"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/Men_of_the_Time,_eleventh_edition',
    )

    list_page_selectors =  'xpath:.//div[@id="mw-content-text"]//table//ul//a[not(@class="new")]/@href'
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]//ul//a[not(@class="new")]/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//span[@id="header_section_text"]//text()',
        'bio': 'clean:xpath:.//div[@id="headerContainer"]/following-sibling::div[1]//text()',
    }

    def refine_item(self, response, item):
        return super(MenOfTimeSpider, self).refine_item(response, item)
