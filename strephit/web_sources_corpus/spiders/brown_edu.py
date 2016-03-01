# -*- coding: utf-8 -*-
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class BrownEduSpider(BaseSpider):
    name = "brown_edu"
    allowed_domains = ["www.brown.edu"]
    start_urls = (
        'https://www.brown.edu/Administration/News_Bureau/Databases/Encyclopedia/',
    )

    custom_settings = {
        'RETRY_HTTP_CODES': ['403'],
        'DOWNLOAD_DELAY': 0.5,
    }

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@class="index"]//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//p[@class="head"]/following-sibling::p[1]/strong/text()',
        'bio': 'clean:xpath:.//div[@class="index"]//text()',
        'other': {
            'credit': 'clean:xpath:.//div[@class="credit"]//text()',
        },
    }

    def refine_item(self, response, item):
        return super(BrownEduSpider, self).refine_item(response, item)
