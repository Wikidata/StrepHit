#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import os
from strephit.commons.logger import logger


def load_scraped_items(items_dir):
    """
    """
    for path, subdirs, files in os.walk(items_dir):
    	for name in files:
            f = os.path.join(path, name)
            with open(f) as source:
                logger.info("Loaded input file '%s'" % name)
                for n, line in enumerate(source):
                    logger.debug("Processing item #%d ..." % n)
                    yield json.loads(line)


def load_corpus(items_dir, document_key):
    """Load an input corpus from a directory with scraped items, in a memory-efficient way.
       Each input file must contain one JSON object per line.
       :param str document_key: a scraped item dictionary key holding textual documents
    """
    for item in load_scraped_items(items_dir):
        document = item.get(document_key)
        if document:
            yield document
        else:
            logger.warning("Skipped item with no textual document. Item: '%s'. Provided item key: '%s'" % (item, document_key))
