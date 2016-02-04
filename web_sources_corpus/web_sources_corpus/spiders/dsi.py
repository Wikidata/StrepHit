# -*- coding: utf-8 -*-
import scrapy

from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus import utils

class DsiSpider(BaseSpider):
    name = "dsi"
    allowed_domains = ["www.uni-stuttgart.de"]
    start_urls = (
        'http://www.uni-stuttgart.de/hi/gnt/dsi2/index.php?table_name=dsi&'
        'function=search&where_clause=&order=lastname&order_type=ASC&page=0',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//a[contains(., "Detail page of this illustrator")]/@href'
    next_page_selectors = 'xpath:.//a[contains(., ">")]/@href'

    item_class = WebSourcesCorpusItem

    def refine_item(self, response, item):
        keys = response.xpath(
            '(.//table)[last()]//tr/td[@class="td_label_details"]//text()'
        ).extract()

        values = response.xpath(
            '(.//table)[last()]//tr/td[@class="td_value_details"]//text()'
        ).extract()

        data = dict(zip((utils.clean(k) for k in keys),
                        (utils.clean(v) for v in values)))
        item['name'] = '%s, %s' % (data.get('Last Name', ''), data.get('Given Name'))
        item['other'] = data

        return item
