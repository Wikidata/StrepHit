# -*- coding: utf-8 -*-
import scrapy

from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem
from strephit.commons import text



class CesarOrgUkSpider(BaseSpider):
    name = "cesar_org_uk"
    allowed_domains = ["cesar.org.uk"]
    start_urls = (
        'http://cesar.org.uk/cesar2/people/people.php?fct=list&search=%25&listMaxRows=999999',
    )

    list_page_selector = None
    next_page_selectors = None
    detail_page_selectors = 'xpath:.//td[@id="keywordColumn"]//a/@href'

    item_class = WebSourcesCorpusItem

    def refine_item(self, response, item):

        item['other'] = {
            'biography': text.extract_dict(response,
                'xpath:.//td[@id="keyColumn"]',
                'xpath:.//td[@id="valueColumn"]'
            ),
            'scripts': [('http://cesar.org.uk/cesar2/titles/titles.php?fct=edit&script_UOID=' +
                            script[len('javascript:scriptClicked('):-1])
                        for script in response.xpath('.//td[@id="keywordColumn"]//a/@href').extract()]
        }

        item['name'] = '%s, %s' % (item['other']['biography'].get('Last name', ''),
                                   item['other']['biography'].get('First name', ''))
 
        return super(CesarOrgUkSpider, self).refine_item(response, item)
