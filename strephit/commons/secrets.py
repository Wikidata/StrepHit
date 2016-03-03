#!/usr/bin/env python
# -*- encoding: utf-8 -*-

from __future__ import absolute_import
import logging


try:
    from secret_keys import *
except (ImportError, AttributeError):
    logging.warn("Some or all secret keys are missing, some components will not work!")
