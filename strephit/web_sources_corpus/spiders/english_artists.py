# -*- coding: utf-8 -*-
import json

from scrapy import Spider, Request

from strephit.web_sources_corpus.items import WebSourcesCorpusItem
from strephit.commons import text


class EnglishArtistsSpider(Spider):
    name = "english_artists"
    allowed_domains = ["en.wikisource.org"]
    start_urls = (
        'https://en.wikisource.org/wiki/A_Dictionary_of_Artists_of_the_English_School',
    )

    def parse(self, response):
        for url in response.xpath(
            './/table[@class="headertemplate"]//p[2]/a[not(@class="new")]/@href'
        ).extract():
            yield Request('https://en.wikisource.org' + url, self.parse_detail)

    def parse_detail(self, response):
        item = None
        for each in response.xpath(
            './/div[@class="tiInherit"]/parent::div/*'
        )[3:]:
            content = each.xpath('child::node()')
            if content and content[0].xpath('local-name()').extract() == ['span']:
                if item:
                    yield self.finalize(item)

                item = WebSourcesCorpusItem(
                    url=response.url,
                    name=' '.join(self.text_from_node(c) for c in content[:3]),
                    bio=text.clean_extract(each, './/text()', sep=' '),
                )

                if each.xpath('./i'):
                    item['other'] = {
                        'profession': text.clean_extract(each, './i//text()')
                    }

                assert item['name'] and len(item['name']) > 3
            elif item:
                item['bio'] += '\n' + text.clean_extract(each, './/text()', sep=' ')

        if item:
            yield self.finalize(item)

    def finalize(self, item):
        if 'other' in item:
            item['other'] = json.dumps(item['other'])
        item['bio'] = text.clean(item['bio'])
        item['name'] = text.clean(','.join(item['name'].split(',')[:-1]))
        return item

    def text_from_node(self, node):
        return (text.clean_extract(node, './/text()', sep=' ')
                if node.xpath('local-name()').extract()
                else text.clean(node.extract()))
