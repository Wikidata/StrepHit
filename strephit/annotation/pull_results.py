#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
import logging
import requests
from pkg_resources import resource_stream
from sys import exit
from zipfile import ZipFile
from StringIO import StringIO
from strephit.commons import secrets
from strephit.commons.logging import log_request_data

logger = logging.getLogger(__name__)


def get_latest_job_id():
    """
    Get the ID of the most recent job.
    :return: the latest job ID
    :rtype: str
    """
    r = requests.get(secrets.CF_JOBS_URL, params={'key': secrets.CF_KEY})
    log_request_data(r, logger)
    r.raise_for_status()
    # The API call returns the 10 latest jobs
    # No way to set a parameter, so return the first element of the list
    return r.json()[0]['id']


def download_full_report(job_id):
    """
    Download the full CSV report of the given job.
    See https://success.crowdflower.com/hc/en-us/articles/202703075-Guide-to-Reports-Page-and-Settings-Page#full_report
    Raises any HTTP error that may occur.
    :param str job_id: job ID registered in CrowdFlower
    """
    params = {
        'key': secrets.CF_KEY,
        'type': 'full'
    }
    r = requests.get(secrets.CF_JOB_RESULTS_URL % job_id, params=params)
    log_request_data(r, logger)
    r.raise_for_status()
    zipped_report = ZipFile(StringIO(r.content))
    zipped_report.extractall()
    return 0


@click.command()
@click.option('--job', '-j', default='latest')
def main(job):
    """
    Download the full CSV report of a CrowdFlower job.
    By default, get the latest job.
    """
    if job == 'latest':
        latest = get_latest_job_id()
        logger.info("Will fetch the report of the latest job ID: %s" % latest)
        download_full_report(latest)
    else:
        download_full_report(job)
    logger.info("Downloaded and decompressed full CSV report in the current directory")
    return 0


if __name__ == '__main__':
    exit(main())
