# -*- coding: utf-8 -*-
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus import utils


class BishopsSpider(BaseSpider):
    name = "bishops"
    allowed_domains = ["www.catholic-hierarchy.org"]
    start_urls = (
        'http://www.catholic-hierarchy.org/bishop/la.html',
    )

    list_page_selectors = 'xpath:.//a[starts-with(@href, "la")]/@href'
    detail_page_selectors = 'xpath:/html/body/ul/li/a[1]/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean_name:clean:xpath:.//h1[@align="center"]//text()',
    }

    def refine_item(self, response, item):
        item['other'] = {
            'microdata': self.parse_microdata(response),
            'bio': self.parse_bio(response),
            'sources': response.xpath(
                './/td/text()[.="Source(s):"]/following-sibling::ul/li/text()'
            ).extract(),
        }
        item['other'].update(self.parse_other(response))

        return super(BishopsSpider, self).refine_item(response, item)

    def parse_other(self, response):
        table = response.xpath('.//table')[1]
        ul_with_caption = table.xpath(
            './/text()[string-length(.) > 1]/following-sibling::ul'
        )

        res = {}
        for ul in ul_with_caption:
            caption = utils.clean_extract(ul, 'preceding-sibling::text()')
            list = ul.xpath('li/child::*').extract()
            res[caption] = list
        res.pop('', None)
        return res

    def parse_bio(self, response):
        table = response.xpath('.//table[@align="center"]')
        fields = [utils.clean_extract(field, './/text()', sep=' ')
                  for field in table.xpath('./tr[1]/th')]
        bio = []
        for table_row in table.xpath('./tr[position()>1]'):
            values = [utils.clean_extract(val, './/text()', sep=' ')
                      for val in table_row.xpath('./td')]
            bio.append(dict(zip(fields, values)))
        return bio

    def parse_microdata(self, response):
        return utils.extract_dict(response,
                                  'xpath:.//section[@id="mdata"]//span',
                                  'xpath:.//section[@id="mdata"]//span',
                                  './@itemprop',
                                  './text()')

    def clean_name(self, response, name):
        if name.endswith(u'†'):
            name = name[:-1].strip()
        return name
