# -*- coding: utf-8 -*-
from web_sources_corpus.spiders import BaseSpider
from web_sources_corpus.items import WebSourcesCorpusItem
from web_sources_corpus import utils


class MedicalBioSpider(BaseSpider):
    name = "medical_bio"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/American_Medical_Biographies',
    )

    list_page_selectors = 'xpath:(.//div[@id="mw-content-text"]//ol)[2]//a/@href'
    detail_page_selectors = 'xpath:.//div[@id="mw-content-text"]//ul//a[not(@class="new")]/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem
    item_fields = {
        'name': 'clean:xpath:.//div[@id="headerContainer"]/following-sibling::div[1]//p[1]/b/text()',
        'bio': 'clean:xpath:.//div[@id="headerContainer"]/following-sibling::div[1]//p[position()>1]//text()',
        'other': {
            'born_died': 'clean:xpath:.//div[@id="headerContainer"]/following-sibling::div[1]//p[1]/text()',
        }
    }

    def refine_item(self, response, item):
        birth, death = utils.parse_birth_death(item['other']['born_died'])
        if birth or death:
            item['birth'] = birth or None
            item['death'] = death or None

        return super(MedicalBioSpider, self).refine_item(response, item)
