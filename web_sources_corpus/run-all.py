import click
import os


@click.command()
@click.argument('spiders-dir', type=click.Path(exists=True, file_okay=False))
@click.argument('data-dir', type=click.Path(exists=True, file_okay=False))
@click.option('--dry-run', '-d', is_flag=True, help='Do not actually run spiders')
@click.option('--skip', '-s', multiple=True, default=['BaseSpider.py', '__init__.py'],
              help='Do not consider these files as valid spiders')
@click.option('--command', '-c', help='Use this command to run the spider',
              default='scrapy crawl -o {data_dir}/{spider}.{format} --logfile {data_dir}/{spider}.log {spider} &')
@click.option('--result-format', '-f', default='jsonlines',
              help='File format used to check for result file presence')
def main(spiders_dir, data_dir, dry_run, skip, command, result_format):
    """ Ensures that all spiders are running, launching them in the background

    Presence/absence of <data-dir>/<spider-name>.json is used to tell if a spider
    needs to be run
    """

    skip = set(skip)

    spiders = set(f[:-len('.py')] for f in os.listdir(spiders_dir)
                  if f.endswith('.py') and f not in skip)
    done = set(f[:-len(result_format)] for f in os.listdir(data_dir) if f.endswith(result_format))
    to_run = spiders.difference(done)

    print 'Detected spiders:'
    print '\t- ' + '\n\t- '.join(spiders) + '\n'

    print 'To-be-run spiders:'
    print '\t- ' + '\n\t- '.join(to_run) + '\n'

    commands = [
        command.format(spider=spider, data_dir=data_dir, format=result_format) for spider in to_run
    ]
    if dry_run:
        print 'Dry run, %d spiders have not been launched' % len(to_run)
        print 'Commands:\n', '\n'.join(commands)
    else:
        print 'Launching spiders...'
        for cmd in commands:
            print cmd
            os.system(cmd)


if __name__ == '__main__':
    main()
