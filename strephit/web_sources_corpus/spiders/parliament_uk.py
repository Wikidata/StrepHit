# -*- coding: utf-8 -*-
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem
from strephit.commons import text


class ParliamentUkSpider(BaseSpider):
    name = "parliament_uk"
    allowed_domains = ["www.parliament.uk"]
    start_urls = (
        'http://www.parliament.uk/mps-lords-and-offices/mps/',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//table//tr/td/a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean_name:clean:xpath:.//div[@id="commons-biography-header"]/h1//text()',
    }

    def refine_item(self, response, item):
        data = {}
        for section in response.xpath('.//div[@class="biography-item-container"]'):
            title = text.clean_extract(section, 'div[1]//h3//text()')
            
            keys = [
                text.clean_extract(td, './/text()')
                for td in section.xpath('./div[2]//table//td[contains(@class, "post")]')
            ]

            values = [
                text.clean_extract(td, './/text()')
                for td in section.xpath('./div[2]//table//td[contains(@class, "date")]')
            ]

            content = zip(keys, values)
            if content:
                data[title] = content

        item['other'] = data

        return super(ParliamentUkSpider, self).refine_item(response, item)

    def clean_name(self, response, name):
        return name[:-len(' MP')] if name.endswith(' MP') else name
