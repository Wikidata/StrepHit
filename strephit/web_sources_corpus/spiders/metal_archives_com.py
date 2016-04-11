# -*- coding: utf-8 -*-
import json
import re

import scrapy
from scrapy import Request

from strephit.web_sources_corpus.items import WebSourcesCorpusItem
from strephit.commons import text


class MetalArchivesComSpider(scrapy.Spider):
    name = "metal_archives_com"
    allowed_domains = ["www.metal-archives.com"]

    base_url = 'http://www.metal-archives.com/search/ajax-artist-search/' \
               '?field=alias&query=%2Aa%2A+OR+%2Ae%2A+OR+%2Ai%2A+OR+%2Ao%2A' \
               '+OR+%2Au%2A&sEcho=1&iDisplayStart={}'

    start_urls = (
        base_url.format(0),
    )

    def parse(self, response):
        current = response.meta.get('count', 0)

        data = json.loads(response.body)
        for artist in data['aaData']:
            to_detail, name, nation, bands = artist
            next_page = re.search(r'<a href="([^"]+)">', to_detail).group(1)
            yield Request(next_page, self.parse_detail)

        if current < data['iTotalRecords']:
            yield Request(self.base_url.format(current + 200), self.parse,
                          meta={'count': current + 200})

    def parse_detail(self, response):
        artist_id = response.url.split('/')[-1]

        keys = response.xpath('.//div[@id="member_info"]//dt')
        values = response.xpath('.//div[@id="member_info"]//dd')
        info = dict((text.clean_extract(k, './/text()'),
                     text.clean_extract(v, './/text()'))
                    for k, v in zip(keys, values))

        item = WebSourcesCorpusItem(
            url=response.url,
            name=info.pop('Real/full name:'),
            other=info,
        )

        yield Request('http://www.metal-archives.com/artist/read-more/id/' + artist_id,
                      self.parse_extern, meta={'item': item, 'field': 'bio', 'aid': artist_id})

    def parse_extern(self, response):
        meta = response.meta
        txt = text.clean_extract(response.selector, './/text()')
        if meta['field'] == 'bio':
            meta['item']['bio'] = txt
            meta['field'] = 'trivia'
            yield Request(
                'http://www.metal-archives.com/artist/read-more/id/%s/field/trivia' % meta['aid'],
                self.parse_extern, meta=meta
            )
        else:  # trivia
            meta['item']['other']['trivia'] = txt
            meta['item']['other'] = json.dumps(meta['item']['other'])
            yield meta['item']
