# -*- coding: utf-8 -*-
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus import utils


class SculptureUkSpider(BaseSpider):
    name = "sculpture_uk"
    allowed_domains = ["sculpture.gla.ac.uk"]
    start_urls = (
        'http://sculpture.gla.ac.uk/browse/index.php',
    )

    list_page_selectors = 'xpath:.//div[@class="featuredpeople"]//a/@href'
    detail_page_selectors = 'xpath:.//div[@class="featured"]/table//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//div[@class="featured"]/h1//text()',
        'birth': 'clean:xpath:.//b[.="Born"]/following-sibling::text()[1]',
        'death': 'clean:xpath:.//b[.="Died"]/following-sibling::text()[1]',
        'bio': 'clean:xpath:.//div[@class="featured"]/p[child::b][last()]/following-sibling::p//text()',
    }

    def refine_item(self, response, item):
        item['other'] = {}
        for section in response.xpath('.//div[@id="content"]//div[@class="featured"][child::h2]'):
            title = utils.clean_extract(section, 'h2//text()')
            content = [utils.clean_extract(p, './/text()') for p in section.xpath('p')]
            item['other'][title] = content

        return super(SculptureUkSpider, self).refine_item(response, item)
