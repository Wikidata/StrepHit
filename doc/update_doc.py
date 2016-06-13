import requests
import click
import subprocess
import os


class WikimediaApi:
    logged_in = False

    def __init__(self, endpoint='https://www.mediawiki.org/w/api.php'):
        self.session = requests.Session()
        self.api_endpoint = endpoint

    def call_api(self, action, **kwargs):
        r = self.session.post(self.api_endpoint + '?format=json&action=' + action,
                              data=kwargs)
        r.raise_for_status()
        return r.json()

    def get_token(self, token_type):
        resp = self.call_api('query', meta='tokens', type=token_type)
        self.logged_in = True
        return resp['query']['tokens'].values()[0]

    def login(self, user, password):
        if not self.logged_in:
            token = self.get_token('login')
            resp = self.call_api('login', lgname=user, lgpassword=password,
                                 lgtoken=token)
            assert resp['login']['result'] == 'Success', \
                'could not login: ' + repr(resp)
            self.logged_in = True

    def logout(self):
        if self.logged_in:
            self.call_api('logout')
            self.logged_in = False


@click.command()
@click.argument('username')
@click.argument('password')
@click.argument('page')
@click.option('--upload/--build-only', default=True)
def main(username, password, page, upload):
    """ Builds the documentation and uploads it to the given mediawiki page
    """
    base_dir = 'build/wikisyntax'

    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip()
    summary = 'doc updated to revision ' + revision
    print 'Current revision is', revision

    print 'Building the documentation ...'
    subprocess.check_output(['make', 'clean', 'apidoc', 'wikisyntax', 'APIDOCOPTS=-f -M -T'],
                            stderr=subprocess.STDOUT)

    page_titles = set([x for x in os.listdir(base_dir) if x not in {'modules.wiki', 'strephit.wiki', 'index.wiki'}])
    pages = ['index.wiki'] + sorted(page_titles)

    content = ''
    for each in pages:
        with open(os.path.join(base_dir, each)) as f:
            content += f.read() + '\n'

    print 'Uploading ...'

    if upload:
        wiki = WikimediaApi()

        try:
            wiki.login(username, password)
            token = wiki.get_token('csrf')
            resp = wiki.call_api('edit',
                                 title=page,
                                 text=content,
                                 contentformat='text/x-wiki',
                                 bot=True, token=token,
                                 summary=summary)
            assert resp.get('edit', {}).get('result') == 'Success', \
                'could not edit: ' + repr(resp)
            print summary
        finally:
            wiki.logout()
    else:
        try:
            with open(page, 'w') as f:
                f.write(content)
        except (OSError, IOError):
            pass

        print summary
        print 'Test run - documentation was NOT updated'


if __name__ == '__main__':
    main()
