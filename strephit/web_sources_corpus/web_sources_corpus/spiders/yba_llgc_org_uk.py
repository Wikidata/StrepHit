# -*- coding: utf-8 -*-
from scrapy import Request
from web_sources_corpus import utils
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem


class YbaLlgcOrgUkSpider(BaseSpider):
    name = "yba_llgc_org_uk"
    allowed_domains = ["yba.llgc.org.uk"]

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@id="text"]/p/a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'bio': 'clean_nu:xpath:.//div[@id="text"]//text()',
        'other': {
            'sources': 'clean_nu:xpath:.//div[@id="text"]/div[@class="biog"]/ul/li[@class="bib_item"]//text()',
            'contributer': 'clean_nu:xpath:.//div[@id="text"]/p[@class="contributer"]//text()',
            'forename': 'clean_nu:xpath:.//div[@id="text"]/span[@class="article_header"]/b/span[@class="forename"]/text()',
            'surname': 'clean_nu:xpath:.//div[@id="text"]/span[@class="article_header"]/b/span[@class="surname"]/text()',
        }
    }

    def start_requests(self):
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            yield Request(
                'http://yba.llgc.org.uk/en/%s/list.html' % letter,
                self.parse)

    def refine_item(self, response, item):
        try:
            dates = utils.clean_extract(
                response, './/div[@id="text"]/span[@class="article_header"]//text()'
            ).split('(')[1].split(')')[0]
        except IndexError:
            pass
        else:
            birth, death = utils.parse_birth_death(dates.replace('\n', ''))
            if birth or death:
                item['birth'] = birth or None
                item['death'] = death or None

        item['name'] = '%s, %s' % (item['other'].pop('forename'),
                                   item['other'].pop('surname'))

        return super(YbaLlgcOrgUkSpider, self).refine_item(response, item)

    def clean_nu(self, response, strings):
        return utils.clean(' '.join(strings).replace('\n', ' '), False)
