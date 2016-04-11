# -*- coding: utf-8 -*-
import re

from scrapy import FormRequest

from strephit.commons import text
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem


class MunksrollSpider(BaseSpider):
    name = "munksroll"
    allowed_domains = ["munksroll.rcplondon.ac.uk"]

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//div[@id="maincontent"]/table//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//h2[@class="PageTitle"]/text()',
        'bio': 'clean:xpath:.//div[@id="prose"]//text()',
    }

    def start_requests(self):
        yield FormRequest('http://munksroll.rcplondon.ac.uk/Biography/Search',
                          self.parse, formdata={'Forename': '', 'Surname': ''})

    def refine_item(self, response, item):
        birth_death = text.clean_extract(response,
                                         './/div[@id="maincontent"]/p[1]/em'
                                         ).split('<br>')[0]

        birth_death = re.subn(r'<[^>]+>', '', birth_death)[0].split('d.')
        if len(birth_death) == 2:
            birth, death = birth_death
            birth = birth[len('b.'):].strip()
            death = death.strip()

            item['birth'] = birth if birth != '?' else None
            item['death'] = death if death != '?' else None

        return super(MunksrollSpider, self).refine_item(response, item)
