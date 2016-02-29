# -*- coding: utf-8 -*-
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class PortraitsAndSketchesSpider(BaseSpider):
    name = "portraits_and_sketches"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/Cartoon_portraits_and_biographical_sketches_of_men_of_the_day',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]//table//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:(.//div[@class="tiInherit"]/p/span)[1]//text()',
        'bio': 'clean:xpath:.//div[@id="headerContainer"]/following-sibling::div[1]//text()',
    }

    def refine_item(self, response, item):
        return super(PortraitsAndSketchesSpider, self).refine_item(response, item)
