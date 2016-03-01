# -*- coding: utf-8 -*-
from scrapy import Item, Field


class WebSourcesCorpusItem(Item):
    name = Field()
    birth = Field()
    death = Field()
    bio = Field()
    url = Field()
    other = Field()
