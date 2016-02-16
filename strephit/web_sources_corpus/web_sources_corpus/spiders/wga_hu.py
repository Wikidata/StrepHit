# -*- coding: utf-8 -*-
import re
from scrapy import Request
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus import utils


class WgaHuSpider(BaseSpider):
    name = "wga_hu"
    allowed_domains = ["www.wga.hu"]

    list_page_selectors = None
    detail_page_selectors = ['xpath:.//table//td[@class="ARTISTLIST"]//a/@href',
                             'xpath:.//a[starts-with(@href, "/bio/")]/@href']
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//div[@class="INDEX2"]/text()',
        'bio': 'clean:xpath:.//h3[.="Biography"]/following-sibling::p/text()',
        'other': {
            'born-died': 'clean:xpath:.//div[@class="INDEX3"]//text()',
        }
    }

    def start_requests(self):
        for letter in 'abcdefghijklmnopqrstuvwxyz':
            yield Request('http://www.wga.hu/cgi-bin/artist.cgi?Profession=any&School' \
                          '=any&Period=any&Time-line=any&from=0&max=9999999&Sort=Name' \
                          '&letter=' + letter, self.parse)

    def refine_item(self, response, item):
        years = re.findall(r'\d+', item['other']['born-died'])
        if len(years) == 2:
            item['birth'] = years[0]
            item['death'] = years[1]
        return super(WgaHuSpider, self).refine_item(response, item)
