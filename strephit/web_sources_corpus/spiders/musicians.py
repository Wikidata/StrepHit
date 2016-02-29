# -*- coding: utf-8 -*-
from strephit.web_sources_corpus.spiders import BaseSpider
from strephit.web_sources_corpus.items import WebSourcesCorpusItem
from strephit.commons import text


class MusiciansSpider(BaseSpider):
    name = "musicians"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/A_Dictionary_of_Music_and_Musicians',
    )

    list_page_selectors = [
        'xpath:.//span[@class="mw-headline"]/parent::h2/following-sibling::ul//a/@href',
        'xpath:.//span[.="Articles"]/parent::h2/following-sibling::ul//a/@href'
    ]
    detail_page_selectors = 'xpath:.//table[@id="multicol"]//a/@href'
    next_page_selectors = None

    item_class = WebSourcesCorpusItem

    def refine_item(self, response, item):
        content = response.xpath('.//div[@id="mw-content-text"]/div[2]')
        children = content.xpath('./p/child::node()')
        if len(children) < 3 or children[2].xpath('local-name()').extract() != ['span']:
            return None
        else:
            name = children[2].xpath('.//text()').extract()
            if name:
                item['bio'] = text.clean_extract(content, './/text()')
                item['name'] = text.clean(children[1].extract() + ' ' + name[0])
            else:
                return None
        return super(MusiciansSpider, self).refine_item(response, item)
