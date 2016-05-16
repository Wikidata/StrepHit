#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import csv
import logging
import re
from sys import exit

import click

logger = logging.getLogger(__name__)

# header with frame + sentence
HEADER = '''<h2 style="text-align:center">{{frame}}</h2>
<blockquote style="text-align:center">{{sentence}}</blockquote>
<hr />

<div class="row">
'''

# closing row div
FOOTER = '</div>'

# token block template
TOKEN_TEMPLATE = '''
    <!-- BEGIN token %(question_num)d -->
    {%% if %(token_field)s != 'No data available' %%}
    <div class="span2">
        <cml:radios label="{{%(token_field)s}}" class="rando" name="name="answer_{{%(token_field)s}}"{{%(token_field)s}}" validates="required" gold="true">

            <cml:radio label="None"></cml:radio>
            %(fe_blocks)s
        </cml:radios>
    </div>
    {%% endif %%}
    <!-- END token %(question_num)d -->
'''

# fe block template
FE_TEMPLATE = '''
            {%% if %(fe_field)s != 'No data available' %%}
            <cml:radio label="{{%(fe_field)s}}"></cml:radio>
            {%% endif %%}
'''


def generate_crowdflower_interface_template(input_csv, output_html):
    """ Generate CrowFlower interface template based on input data spreadsheet

    :param file input_csv: CSV file with the input data
    :param output_html: File in which to write the output
    :type output_html: file
    :return: 0 on success
    """
    # Get the filed names of the input data spreadsheet
    sheet = csv.DictReader(input_csv)
    fields = sheet.fieldnames
    # Get "fe_[0-9][0-9]" fields
    fe_fields = [f for f in fields if re.match(r'fe_[0-9]{2}$', f)]
    # Get "chunk[0-9][0-9]" fields
    token_fields = [f for f in fields if re.match(r'chunk_[0-9]{2}$', f)]
    # Generate fe blocks for every token field
    fe_blocks = []
    for fe_field in fe_fields:
        fe_blocks.append(FE_TEMPLATE % {'fe_field': fe_field})
    crowdflower_interface_template = HEADER
    # Generate fe_name blocks(question blocks) for every fe_name field
    for idx, token_field in enumerate(token_fields):
        dic = {'question_num': idx + 1, 'token_field': token_field}
        # Add fe blocks into template
        dic['fe_blocks'] = ''.join(fe_blocks)
        # Add current fe_name block or question block into template
        crowdflower_interface_template += (TOKEN_TEMPLATE % dic)

    crowdflower_interface_template += FOOTER
    output_html.write(crowdflower_interface_template)
    return 0


@click.command()
@click.argument('input_csv', type=click.File())
@click.option('--outfile', '-o', type=click.File('w'), default='dev/cml.html')
def main(input_csv, outfile):
    """Generate CML interface template"""
    generate_crowdflower_interface_template(input_csv, outfile)
    return 0


if __name__ == '__main__':
    exit(main())
