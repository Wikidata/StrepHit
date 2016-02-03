# -*- coding: utf-8 -*-
from web_sources_corpus import utils
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem

class NewulsterbiographyCoUkSpider(BaseSpider):
    name = "newulsterbiography_co_uk"
    allowed_domains = ["www.newulsterbiography.co.uk"]
    start_urls = (
        'http://www.newulsterbiography.co.uk/index.php/home/browse/all',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@id="search_results"]/p/a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'get_name:xpath:.//h1[@class="person_heading"]/br/preceding-sibling::text()',
        'bio': 'get_bio:xpath:.//div[@id="person_details"]/div/br[1]/preceding-sibling::*//text()',
        'birth': 'clean:xpath:.//div[@id="person_details"]/div/table[2]//tr[1]/td[2]/text()',
        'death': 'clean:xpath:.//div[@id="person_details"]/div/table[2]//tr[2]/td[2]/text()',
        'other': {
            'profession': 'xpath:.//span[@class="person_heading_profession"]//text()'
        },
    }

    def get_bio(self, response, values):
        bio = utils.clean('\n'.join(reversed(values)))

        if not bio:
            bio = utils.clean_extract(
                response,
                './/div[@id="person_details"]/div/br[1]/preceding-sibling::text()'
            )

        assert bio
        return bio

    def get_name(self, response, values):
        if not values:
            values = response.xpath('//h1[@class="person_heading"]/text()').extract()
        return values[0].split('(')[0].strip()
