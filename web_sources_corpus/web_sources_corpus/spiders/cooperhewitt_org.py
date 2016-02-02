# -*- coding: utf-8 -*-

from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus.spiders.BaseSpider import BaseSpider


class CooperhewittOrgSpider(BaseSpider):
    name = "cooperhewitt_org"
    allowed_domains = ["collection.cooperhewitt.org"]
    start_urls = (
        'http://collection.cooperhewitt.org/people/page1',
    )

    list_page_selectors = None
    detail_page_selectors = 'get_detail_page:xpath:.//div[@class="row"]/div[2]/ul[@class="list-o-things"]//h1/a/@href'
    next_page_selectors = 'xpath:.//ul[@class="pagination"]/li[last()]/a/@href'

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//div[@class="page-header"]/h1/a/text()',
        'bio': 'clean:xpath:.//div[contains(@class, "person-bio")]/p//text()',
    }

    def get_detail_page(self, response, urls):
        return (url + 'bio' for url in urls)

    def refine_item(self, response, item):
        if item['bio']:
            return item
        else:
            return None
