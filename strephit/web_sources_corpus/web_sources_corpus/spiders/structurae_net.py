# -*- coding: utf-8 -*-
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus import utils


class StructuraeNetSpider(BaseSpider):
    name = "structurae_net"
    allowed_domains = ["structurae.net"]
    start_urls = (
        'http://structurae.net/persons/',
    )

    list_page_selectors = 'xpath:.//ol[@class="commalist"]//a/@href'
    detail_page_selectors = 'xpath:.//ol[@class="searchlist"]//a/@href'
    next_page_selectors = 'xpath:(.//div[@class="nextPageNav"])[1]//a[1]/@href'

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//h1/span[@itemprop="name"]//text()',
        'other': {
            'publications': 'xpath:.//div[@id="person-literature"]//li//a/@href',
            'websites': 'xpath:.//div[@id="person-websites"]//li/a/@href',
            'bibliography': 'xpath:.//div[@id="person-bibliography"]//li/a/@href',
            'participated_in': 'xpath:.//div[@id="person-references"]//a/@href',
        },
    }

    def refine_item(self, response, item):
        data = utils.extract_dict(response,
            'xpath:.//div[@id="person-chronology"]//table//th',
            'xpath:.//div[@id="person-chronology"]//table//td',
            sep=' '
        )

        item['other']['publications'] = [self.make_url_absolute(response.url, url)
                                         for url in item['other']['publications']]
        item['other']['websites'] = [self.make_url_absolute(response.url, url)
                                         for url in item['other']['websites']]
        item['other']['bibliography'] = [self.make_url_absolute(response.url, url)
                                         for url in item['other']['bibliography']]
        item['other']['participated_in'] = [self.make_url_absolute(response.url, url)
                                         for url in item['other']['participated_in']]

        item['other']['biography'] = data

        item['birth'] = data.get('Born in')
        item['death'] = data.get('Deceased in', data.get('Deceased on'))

        return super(StructuraeNetSpider, self).refine_item(response, item)
