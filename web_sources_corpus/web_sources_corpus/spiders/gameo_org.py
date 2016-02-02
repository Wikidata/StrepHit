# -*- coding: utf-8 -*-
import json
import re
import logging
from web_sources_corpus import utils
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus.spiders.BaseSpider import BaseSpider


class GameoOrgSpider(BaseSpider):
    name = "gameo_org"
    allowed_domains = ["gameo.org"]
    start_urls = (
        'http://gameo.org/index.php?title=Special:AllPages&from='
        '108+Chapel+%28100+Mile+House%2C+British+Columbia%2C+Canada%29',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//table[@class="mw-allpages-table-chunk"]//a/@href'
    next_page_selectors = 'xpath:.//td[@class="mw-allpages-nav"]/a[3]/@href'

    item_class = WebSourcesCorpusItem
    item_fields = {
        'bio': 'clean:xpath:.//div[@id="mw-content-text"]/h1[1]/preceding-sibling::*//text()'
    }

    def refine_item(self, response, item):
        try:
            title = utils.clean_extract(response.selector, './/h1[@id="firstHeading"]//text()')
            name, birth, death = self.parse_title(title)
        except (IndexError, ValueError):
            # not a person (could be a place or whatever else)
            logging.debug('Not a person at ' + response.url)
            return None
        else:
            item['name'] = name
            item['birth'] = birth
            item['death'] = death
            item['other'] = json.dumps({'title': title})
            return item

    def parse_title(self, title):
        name, info = title.split('(')
        if info.startswith('d.'):
            birth, death = None, re.findall(r'\d+', info)[0]
        elif info.startswith('b.'):
            birth, death = re.findall(r'\d+', info)[0], None
        elif 'century' in info:
            birth, death = None, None
        else:
            birth, death = re.findall(r'(\d+)-(\d*)', info.replace(' ', ''))[0]
        return name.strip(), birth, death
