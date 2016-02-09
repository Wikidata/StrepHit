#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import logging


def setup_logger(level='info', log_file=None):
    """ Convenience function for a reasonable logging configuration
        The default level is INFO
    """
    levels = {'info': logging.INFO, 'warning': logging.WARNING, 'debug': logging.DEBUG}
    logger = logging.getLogger()
    logger.setLevel(levels[level])
    # Message format, shared among handlers
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(module)s.%(funcName)s #%(lineno)d - %(message)s")
    # Log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)
    # Log to file
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(log_formatter)
        logger.addHandler(file_handler)
    return logger


# Default logger: write to console with level INFO
default_logger = setup_logger()