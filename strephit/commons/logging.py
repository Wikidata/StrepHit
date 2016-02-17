#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
import tempfile
import sys
import logging
import logging.config
import yaml
import os


LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'WARN': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}


def setup():
    logging.config.dictConfig({
        'version': 1, 
        'disable_existing_loggers': False, 
        'loggers': {
            '': {
                'level': 'WARNING', 
                'handlers': ['console', 'debug_file_handler']
            }, 
            'strephit': {
                'level': 'INFO', 
            },
        }, 
        'formatters': {
            'strephit': {
                'format': '%(asctime)s [%(levelname)s] %(module)s.%(funcName)s #%(lineno)d - %(message)s'
            }
        }, 
        'handlers': {
            'console': {
                'formatter': 'strephit', 
                'class': 'logging.StreamHandler', 
                'level': 'DEBUG'
            }, 
            'debug_file_handler': {
                'formatter': 'strephit',
                'level': 'DEBUG', 
                'filename': 'strephit-debug.log', 
                'mode': 'w',
                'class': 'logging.FileHandler', 
                'encoding': 'utf8'
            }
        }
    })


def setLogLevel(module, level):
    """ Sets the log level used to log messages from the given module """
    if level in LEVELS:
        module = '' if module == 'root' else module
        logging.getLogger(module).setLevel(level)
