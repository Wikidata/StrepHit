#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
import tempfile
import requests
import hashlib
import click
import json
import os
import logging
import tarfile
from strephit.commons import cache


logger = logging.getLogger(__name__)


def load_scraped_items(location):
    """ Loads all the items from a directory or file.
    :param location: Where is the corpus. If it is a directory, all files with extension
    jsonlines will be loaded. Otherwise, if it is a file, it can be either a jsonlines
    of a tar compressed file.
    """
    def list_files():
        if os.path.isfile(location):
            if tarfile.is_tarfile(location):
                tar = tarfile.open(location)
                for file in tar:
                    yield file.name, tar.extractfile(file)
            else:
                yield location, location
        else:
            for name in os.listdir(location):
                if name.endswith('.jsonl') or name.endswith('.jsonlines'):
                    yield name, os.path.join(location, name)

    def process_stream(name, stream):
        logger.info("Loaded input file '%s'" % name)
        for n, line in enumerate(stream):
            logger.debug("Processing item #%d ..." % n)
            try:
                yield json.loads(line)
            except ValueError:
                logger.warn('cannot load item at row %d of file %s' % (n, name))

    for name, file in list_files():
        if hasattr(file, 'read'):
            try:
                for each in process_stream(name, file):
                    yield each
            finally:
                file.close()
        else:
            with open(file) as f:
                for each in process_stream(name, f):
                    yield each

    logger.debug('all items loaded')


# Sometimes the document may be a list of strings, depending on how it was scraped
def _join_text(document):
    if type(document) == list:
        logger.debug("Text document as a list, will convert it into a string: %s" % document)
        return '\n'.join(document)
    else:
        return document


def load_corpus(items_dir, document_key, text_only=False):
    """ Load an input corpus from a directory with scraped items, in a memory-efficient way.
        Each input file must contain one JSON object per line.
        :param str document_key: a scraped item dictionary key holding textual documents
    """
    for item in load_scraped_items(items_dir):
        document = item.get(document_key)
        if document:
            document = _join_text(document)
            if text_only:
                yield document
            else:
                # Do not lose essential metadata, i.e., name and URL
                yield {'name': item.get('name'), 'url': item.get('url'), document_key: document}
        else:
            logger.debug("Skipped item with no text document: '%s'. Provided item key: '%s'" % (item, document_key))


def load_dumped_corpus(dump_file_handle, document_key, text_only=False):
    """ Load a previously dumped corpus file, in a memory-efficient way. """
    for line in dump_file_handle:
        item = json.loads(line)
        # The document key should always exist here, so raise KeyError if not
        document = _join_text(item[document_key])
        if text_only:
            yield document
        else:
            item[document_key] = document
            yield item


def dump_corpus(corpus, dump_file_handle):
    """ Dump a loaded corpus to a file with one JSON object per line ."""
    logger.info("Will dump corpus to '%s' ... Format: JSON objects with metadata, one per line" % dump_file_handle.name)
    for item in corpus:
        dump_file_handle.write(json.dumps(item) + '\n')
    return 0


def get_and_cache(url, use_cache=True, cache_base='strephit_cache', **kwargs):
    """
    Perform an HTTP GET request to the given url and optionally cache the
    result somewhere in the file system. The cached content will be used
    in the subsequent requests.
    Raises all HTTP errors
    :param url: URL of the page to retrieve
    :param use_cache: Whether to use cache
    :param **kwargs: keyword arguments to pass to `requests.get`
    :return: The content page at the given URL, unicode
    """
    if not use_cache:
        r = requests.get(url, **kwargs)
        r.raise_for_status()
        content = r.text
    else:
        key = url + json.dumps(kwargs)
        content = cache.get(key)
        if content is None:
            content = get_and_cache(url, use_cache=False, **kwargs)
            cache.set(key, content)
    return content
