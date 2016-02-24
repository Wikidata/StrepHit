# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy import Item, Field


class WebSourcesCorpusItem(Item):
    name = Field()
    birth = Field()
    death = Field()
    bio = Field()
    url = Field()
    other = Field()
