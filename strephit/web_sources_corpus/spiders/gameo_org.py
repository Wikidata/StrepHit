# -*- coding: utf-8 -*-
import json
import logging
from strephit.commons import text
from strephit.web_sources_corpus.items import WebSourcesCorpusItem
from strephit.web_sources_corpus.spiders.BaseSpider import BaseSpider


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
            title = text.clean_extract(response.selector, './/h1[@id="firstHeading"]//text()')
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
        birth, death = text.parse_birth_death(info)
        return name.strip(), birth, death
