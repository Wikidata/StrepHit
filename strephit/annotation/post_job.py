#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import click
import json
import logging
import requests
from strephit.commons import secrets
from strephit.commons.logging import log_request_data
from pkg_resources import resource_stream
from sys import exit
from urllib import unquote_plus

logger = logging.getLogger(__name__)


def create_job(title, instructions, cml, custom_js):
    """
     Create an empty CrowdFlower job with the specified title and instructions.
     Raise any HTTP error that may occur.
     :param str title: plain text title
     :param str instructions: instructions, can contain HTML
     :param str cml: worker interface CML template. See https://success.crowdflower.com/hc/en-us/articles/202817989-CML-CrowdFlower-Markup-Language-Overview
     :param str custom_js: JavaScript code to be injected into the job
     :return: the created job response object, as per https://success.crowdflower.com/hc/en-us/articles/201856229-CrowdFlower-API-API-Responses-and-Messaging#job_response
     :rtype: dict
    """
    data = {
        'key': secrets.CF_KEY,
        'job[title]': title,
        'job[instructions]': instructions,
        'job[cml]': cml,
        'job[js]': custom_js
    }
    r = requests.post(secrets.CF_JOBS_URL, data=data)
    log_request_data(r, logger)
    r.raise_for_status()
    return r.json()


def upload_units(job_id, csv_data):
    """
     Upload the job data units to the given job.
     Raises any HTTP error that may occur.
     :param str job_id: job ID registered in CrowdFlower
     :param file csv_data: file handle pointing to the data units CSV
     :return: the uploaded job response object, as per https://success.crowdflower.com/hc/en-us/articles/201856229-CrowdFlower-API-API-Responses-and-Messaging#job_response
     :rtype: dict
    """
    headers = {'Content-Type': 'text/csv'}
    params = { 'key': secrets.CF_KEY }
    r = requests.put(secrets.CF_JOB_UPLOAD_URL % job_id, data=csv_data, headers=headers, params=params)
    log_request_data(r, logger)
    r.raise_for_status()
    return r.json()


@click.command()
@click.argument('csv_data', type=click.File())
@click.option('--title', '-t', default='Understand the Meaning of Words')
@click.option('--instructions', '-i', type=click.File(), default=resource_stream(__name__, 'resources/instructions.html'))
@click.option('--cml', '-c', type=click.File(), default=resource_stream(__name__, 'resources/cml.html'))
@click.option('--javascript', '-j', type=click.File(), default=resource_stream(__name__, 'resources/randomize.js'))
def main(csv_data, title, instructions, cml, javascript):
    """ Post a CrowdFlower annotation job with title, instructions, CML interface template, custom JavaSctipt, and data units """
    logger.info("Creating CrowdFlower job ...")
    job = create_job(title, ''.join(instructions.readlines()), ''.join(cml.readlines()), ''.join(javascript.readlines()))
    logger.debug("Job object response from CrowdFlower: %s" % json.dumps(job, indent=2))
    job_id = job['id']
    logger.info("Uploading data units from '%s' to job ID %d ..." % (csv_data.name, job_id))
    uploaded = upload_units(job_id, csv_data)
    logger.debug("Job object response from CrowdFlower: %s" % json.dumps(uploaded, indent=2))
    return 0


if __name__ == '__main__':
    exit(main())
