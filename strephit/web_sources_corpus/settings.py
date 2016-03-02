# -*- coding: utf-8 -*-
BOT_NAME = 'strephit'

SPIDER_MODULES = ['strephit.web_sources_corpus.spiders']
NEWSPIDER_MODULE = 'strephit.web_sources_corpus.spiders'
TEMPLATES_DIR = 'strephit/web_sources_corpus/templates/'

USER_AGENT = 'strephit (+https://github.com/Wikidata/StrepHit)'
CONCURRENT_REQUESTS=8
AUTOTHROTTLE_ENABLED=True
AUTOTHROTTLE_START_DELAY=5
AUTOTHROTTLE_MAX_DELAY=60
AUTOTHROTTLE_DEBUG=False
HTTPCACHE_ENABLED=True
HTTPCACHE_EXPIRATION_SECS=0
HTTPCACHE_DIR='/tmp/strephit_cache/scrapy-httpcache'
