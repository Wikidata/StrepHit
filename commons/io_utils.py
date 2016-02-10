#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import os
from commons.logger import logger


def load_corpus(corpus_dir):
    """Load an input corpus from a directory.
       Each input file must contain one JSON object per line.
    """    
    for path, subdirs, files in os.walk(corpus_dir):
    	for name in files:
            f = os.path.join(path, name)
            with open(f) as source:
                logger.info("Loaded input file '%s'" % name)
                for n, line in enumerate(source):
                    logger.debug("Processing item #%d ..." % n)
                    yield json.loads(line)
