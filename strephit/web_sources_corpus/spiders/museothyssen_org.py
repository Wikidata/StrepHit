# -*- coding: utf-8 -*-
import re

from strephit.commons import text
from strephit.web_sources_corpus.items import WebSourcesCorpusItem
from strephit.web_sources_corpus.spiders import BaseSpider


class MuseothyssenOrgSpider(BaseSpider):
    name = "museothyssen_org"
    allowed_domains = ["www.museothyssen.org"]
    start_urls = (
        'http://www.museothyssen.org/en/thyssen/artistas',
    )

    list_page_selectors = None
    detail_page_selectors = 'xpath:.//ul[@id="autoresAZ"]/li/ul/li/a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//dl[@class="datosAutor"]/dt[contains(., "Author:")]/following-sibling::dd[1]//text()',
        'bio': 'clean:xpath:.//span[@id="contReader1"]//text()',
        'other': {
            'born': 'clean:xpath:.//dl[@class="datosAutor"]/dt[contains(., "Born/Dead:")]/following-sibling::dd[1]//text()',
        },
    }

    def refine_item(self, response, item):
        born = item['other']['born']
        if born:
            birth, death = text.parse_birth_death(
                born.split(',')[-1]
            )
            if birth or death:
                if birth and death and len(death) == 2:
                    # catch dates like 1515-35
                    death = birth[0:2] + death
                item['birth'] = birth
                item['death'] = death
            else:
                try:
                    birth, death = born.split('-', 1)
                    m = re.search(r'\d{3,4}$', birth.strip())
                    item['birth'] = m.group(0) if m else None

                    m = re.search(r'\d{3,4}$', death.strip())
                    item['death'] = m.group(0) if m else None
                except ValueError:
                    pass

        return item
