#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import logging
from sys import exit

import click
import requests
from pkg_resources import resource_stream

from strephit.commons import secrets
from strephit.commons.logging import log_request_data

logger = logging.getLogger(__name__)

# TODO consider adding "job[auto_order]": "true" for automatic ordering

# Enable English-speaking workers from:
# Australia, Canada, Denmark, Finland, Great Britain, Gibraltar,
# Ireland, Iceland, Malta, Norway, New Zealand, Sweden, United States,
# South Africa
INCLUDED_COUNTRIES = [
    "AU", "CA", "DK", "FI",
    "GB", "GI", "IE", "IS",
    "MT", "NO", "NZ", "SE",
    "US", "ZA"
    ]

JOB_SETTINGS = {
    "job[judgments_per_unit]": 1,
    "language": "en",
    "job[max_judgments_per_worker]": 500,
    "job[minimum_requirements][min_score]": 1,
    "job[minimum_requirements][priority]": 1,
    "job[minimum_requirements][skill_scores][it_crowd_official]": 1,
    # Worker levels
    # In all levels workers must have answered > 100 test questions
    # Level 1: > 70% accuracy
    # Level 2: > 80% accuracy
    # Level 3: > 85% accuracy
    "job[minimum_requirements][skill_scores][level_1_contributors]": 1,
    "job[options][after_gold]": "2",
    # Minimum time per page = 20 seconds
    "job[options][calibrated_unit_time]": "20",
    "job[options][include_unfinished]": "true",
    "job[options][logical_aggregation]": "true",
    "job[options][mail_to]": "fossati@fbk.eu",
    # Minimum worker accuracy = 40 % (2/5 test questions to pass)
    "job[options][reject_at]": "40",
    "job[options][req_ttl_in_seconds]": 900,
    "job[options][track_clones]": "true",
    "job[pages_per_assignment]": 1,
    # Payment per page
    "job[payment_cents]": 5,
    # Units per page
    "job[units_per_assignment]": 5,
}


def create_job(title, instructions, cml, custom_js):
    """
     Create an empty CrowdFlower job with the specified title and instructions.
     Raise any HTTP error that may occur.

     :param str title: plain text title
     :param str instructions: instructions, can contain HTML
     :param str cml: worker interface CML template. See https://success.crowdflower.com/hc/en-us/articles/202817989-CML-CrowdFlower-Markup-Language-Overview
     :param str custom_js: JavaScript code to be injected into the job
     :return: the created job response object, as per https://success.crowdflower.com/hc/en-us/articles/201856229-CrowdFlower-API-API-Responses-and-Messaging#job_response on success, or an error message
     :rtype: dict
    """
    data = {
        "key": secrets.CF_KEY,
        "job[title]": title,
        "job[instructions]": instructions,
        "job[cml]": cml,
        "job[js]": custom_js,
    }
    r = requests.post(secrets.CF_JOBS_URL, data=data)
    log_request_data(r, logger)
    r.raise_for_status()
    return r.json()


def config_job(job_id):
    """
     Setup a given CrowdFlower job with default settings.
     See :const: JOB_SETTINGS

     :param str job_id: job ID registered in CrowdFlower
     :return: the uploaded job response object, as per https://success.crowdflower.com/hc/en-us/articles/201856229-CrowdFlower-API-API-Responses-and-Messaging#job_response on success, or an error message
     :rtype: dict
    """
    params = {'key': secrets.CF_KEY}
    # Manually prepare the body, due to multiple included countries
    # i.e., requests will ignore dicts with the same key
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = '&'.join("job[included_countries][]=%s" % c for c in INCLUDED_COUNTRIES) + '&' + \
           '&'.join('%s=%s' % param for param in JOB_SETTINGS.iteritems())
    r = requests.put(secrets.CF_JOB_CONFIG_URL % job_id, headers=headers, params=params, data=data)
    log_request_data(r, logger)
    r.raise_for_status()
    return r.json()


def upload_units(job_id, csv_data):
    """
     Upload the job data units to the given job.
     Raises any HTTP error that may occur.

     :param str job_id: job ID registered in CrowdFlower
     :param file csv_data: file handle pointing to the data units CSV
     :return: the uploaded job response object, as per https://success.crowdflower.com/hc/en-us/articles/201856229-CrowdFlower-API-API-Responses-and-Messaging#job_response on success, or an error message
     :rtype: dict
    """
    headers = {'Content-Type': 'text/csv'}
    params = {'key': secrets.CF_KEY}
    r = requests.put(secrets.CF_JOB_UPLOAD_URL % job_id, data=csv_data, headers=headers, params=params)
    log_request_data(r, logger)
    r.raise_for_status()
    return r.json()


def convert_gold(job_id):
    """
     Activate gold units in the given job.
     Corresponds to the 'Convert Uploaded Test Questions' UI button.

     :param str job_id: job ID registered in CrowdFlower
     :return: True on success
     :rtype: boolean
    """
    params = {'key': secrets.CF_KEY}
    r = requests.put(secrets.CF_JOB_ACTIVATE_GOLD_URL % job_id, params=params)
    log_request_data(r, logger)
    # Inconsistent API: returns 406, but actually sometimes works (!!!)
    if r.status_code == 406:
        return r.json()
    else:
        r.raise_for_status()


def tag_job(job_id, tags):
    """
     Tag a given job.

     :param str job_id: job ID registered in CrowdFlower
     :param list tags: list of tags
     :return: True on success
     :rtype: boolean
    """
    params = {'key': secrets.CF_KEY}
    data = {"tags": tags}
    r = requests.post(secrets.CF_JOB_TAG_URL % job_id, params=params, data=data)
    log_request_data(r, logger)
    r.raise_for_status()
    return r.ok


@click.command()
@click.argument('csv_data', type=click.File())
@click.option('--title', '-t', default='Make Sense of Sentences')
@click.option('--instructions', '-i', type=click.File(),
              default=resource_stream(__name__, 'resources/instructions.html'))
@click.option('--cml', '-c', type=click.File(), default=resource_stream(__name__, 'resources/cml.html'))
@click.option('--javascript', '-j', type=click.File(), default=resource_stream(__name__, 'resources/randomize.js'))
@click.option('--tags', help="Comma-separated list of job tags")
@click.option('--activate-gold', is_flag=True, default=False, help="Activate test questions")
@click.option('--disable-quiz-mode', is_flag=True, default=False)
def main(csv_data, title, instructions, cml, javascript, tags, activate_gold, disable_quiz_mode):
    """ Post a CrowdFlower annotation job with title, instructions,
        CML interface template, custom JavaSctipt, and data units
    """
    logger.info("Creating CrowdFlower job ...")
    if disable_quiz_mode:
        JOB_SETTINGS['quiz_mode_enabled'] = False
        logger.info("Quiz mode disabled")
    job = create_job(title, ''.join(instructions.readlines()), ''.join(cml.readlines()),
                     ''.join(javascript.readlines()))
    logger.debug("Job object response from CrowdFlower: %s" % json.dumps(job, indent=2))
    job_id = job['id']
    if tags:
        logger.info("Tagging job with '%s' ..." % tags)
        tagged = tag_job(job_id, tags)
        logger.debug("CrowdFlower API response: %s" % json.dumps(tagged, indent=2))
    logger.info("Uploading data units from '%s' to job ID %d ..." % (csv_data.name, job_id))
    uploaded = upload_units(job_id, csv_data)
    logger.debug("Job ID %d object response from CrowdFlower: %s" % (job_id, json.dumps(uploaded, indent=2)))
    if activate_gold:
        logger.info("Activating gold units ...")
        activated = convert_gold(job_id)
        logger.debug("CrowdFlower API inconsistent response: %s" % json.dumps(activated, indent=2))
    logger.info("Setting up job parameters ...")
    configurated = config_job(job_id)
    logger.debug("Updated job ID %d object: %s" % (job_id, json.dumps(configurated, indent=2)))
    return 0


if __name__ == '__main__':
    exit(main())
