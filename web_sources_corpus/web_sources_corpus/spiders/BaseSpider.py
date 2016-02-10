# -*- coding: utf-8 -*-

import scrapy
import urlparse
import re
import json
from scrapy import Request
from web_sources_corpus import utils


class BaseSpider(scrapy.Spider):
    """ Generic base spider, to abstract most of the work.
    Specify the selectors to suit the website to scrape. The spider first uses
    a list of selectors to reach a page containing the list of items to scrape.
    Another selector is used to extract urls pointing to detail pages, containing
    the details of the items to scrape. Finally a third selector is used to
    extract the url pointing to the next "list" page.

     - `list_page_selectors` is a list of selectors used to reach the page
       containing the items to scrape. Each selector is applied to the page(s)
       fetched by extracting the url from the previous page using the preceding
       selector.
     - `detail_page_selectors` extract the urls pointing to the detail pages. Can be
       a single selector or a list.
     - `next_page_selectors` extracts the url pointing to the next page

    Selector starting with `css:` are css selectors, those starting with `xpath:`
    are xpath selectors, all others should follow the syntax `method:selector`,
    where `method` is the name of a method of the spider and `selector` is another
    selector specified in the same way as above). The method is used to transform
    the result obtained by extracting the item pointed by the selecctor and should
    accept the response as first parameter and the result of extracting the data
    pointed by the selector (only if specified).

    The spider provides a simple method to parse items. Item class is specified in
    `item_class` (must inherit from `scrapy.Item`) and item fields are specified
    in the dict `item_fields`, whose keys are field names and values are selectors
    following the syntax described above. They can also be lists or dicts arbitrarily
    nested eventually containing selectors.

    Each item can be processed and refined by the method `refine_item`.
    """
    list_page_selectors = None
    detail_page_selectors = None
    next_page_selectors = None

    item_class = None
    item_fields = {

    }

    def parse(self, response):
        """ First stage of the spider with the goal of reaching the list page.
        """
        next_pages = response.meta.get('next_pages', self.list_page_selectors)
        if not next_pages:
            # we have reached the page with the list of items
            for each in self.parse_list(response):
                yield each
        else:
            # still some pages to scrape before reaching the list of items
            if type(next_pages) == list:
                selector, rest = next_pages[0], next_pages[1:]
                save = {'next_pages': rest}
            else:
                selector = next_pages
                save = {'next_pages': None}

            for url in self.get_elements_from_selector(response, selector):
                yield Request(self.make_url_absolute(response.url, url), self.parse,
                              meta=save)

    def parse_list(self, response):
        """ Second stage of the spider implementing pagination
        """
        if type(self.detail_page_selectors) == list:
            selector, rest = self.detail_page_selectors[0], self.detail_page_selectors[1:]
            save = {'next_pages': rest}
        else:
            selector = next_pags
            save = {'next_pages': None}

        for url in self.get_elements_from_selector(response, selector):
            yield Request(self.make_url_absolute(response.url, url), self.parse_detail,
                          meta=save)

        if self.next_page_selectors:
            _next = self.get_elements_from_selector(response, self.next_page_selectors)
            if _next:
                yield Request(self.make_url_absolute(response.url, _next[0]),
                              self.parse_list)

    def parse_detail(self, response):
        """ Third stage of the spider, parses the detail page to produce an item
        """

        def make_dict(fields, result=None):
            res = result or {}
            for k, v in fields.iteritems():
                if type(v) == dict:
                    res[k] = make_dict(v)
                elif type(v) == list:
                    res[k] = map(make_dict, v)
                else:
                    res[k] = self.get_elements_from_selector(response, v)
            return res
    
        next_pages = response.meta.get('next_pages')
        if next_pages:
            selector, rest = next_pages[0], next_pages[1:]
            for url in self.get_elements_from_selector(response, selector):
                yield Request(self.make_url_absolute(response.url, url),
                              self.parse_detail, meta={'next_pages': rest})
        else:
            item = make_dict(self.item_fields, self.item_class(url=response.url))
            yield self.refine_item(response, item)

    def refine_item(self, response, item):
        """ Applies any custom post-processing to the item, override if needed.
        Return None to discard the item
        """
        if item.get('other') is not None:
            item['other'] = json.dumps(item['other'])
        return item

    def get_elements_from_selector(self, response, selector):
        if type(selector) == list:
            return [self.get_elements_from_selector(response, sel)
                    for sel in selector]
        else:
            assert selector is not None
            if selector.startswith('css:'):
                return response.css(selector[len('css:'):]).extract()
            elif selector.startswith('xpath:'):
                return response.xpath(selector[len('xpath:'):]).extract()
            else:
                method, selector = selector.split(':', 1)
                if selector:
                    result = self.get_elements_from_selector(response, selector)
                    return getattr(self, method)(response, result)
                else:
                    return getattr(self, method)(response)

    def make_url_absolute(self, page_url, url):
        splitted = urlparse.urlsplit(url)
        if splitted.netloc:  # already absolute
            return url
        else:
            return urlparse.urljoin(page_url, url)

    def clean(self, response, strings, unicode=True):
        """ Utility function to clean strings. Can be used within your selectors
        """
        return utils.clean(' '.join(strings), unicode)
