# -*- coding: utf-8 -*-
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus import utils


class AcademiaNetSpider(BaseSpider):
    name = "academia_net"
    allowed_domains = ["www.academia-net.org"]
    start_urls = (
        'http://www.academia-net.org/search/?sv%5Barea_id%5D%5B0%5D=1252&sv%5Br_rbs_fachgebiete%5D%5B0%5D=&_seite=1',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//li[@class="profil"]/div[1]/a/@href'
    next_page_selectors = 'xpath:.//div[@class="jumplist"]/a[last()]/@href'

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//h1[contains(@class, "profilname")]/text()',
    }

    def refine_item(self, response, item):
        item['other'] = {}
        for ul in response.xpath(
                './/div[@id="stammdaten"]/div[contains(@class, "text")]//ul'
            ):
            field = ul.xpath('preceding-sibling::h4/text()').extract()[-1]
            value = [
                utils.clean_extract(li, './/text()', sep=' ') for li in ul.xpath('li')
            ]
            item['other'][field] = value


        for section in response.xpath('.//div[@class="section"]'):
            title = utils.clean_extract(section, 'div[1]//text()')
            values = [utils.clean_extract(li, './/text()')
                      for li in section.xpath('div[2]/ul/li')]
            if values:
                item['other'][title] = values

        item['name'] = utils.clean(item['name'].replace('\t', ' '))
        
        return super(AcademiaNetSpider, self).refine_item(response, item)
