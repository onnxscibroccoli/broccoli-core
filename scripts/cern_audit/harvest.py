"""Read-only GitHub metadata collection; no third-party Python dependencies."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request


class API:
    def __init__(self, token, budget=2000):
        self.token, self.budget, self.requests = token, budget, 0

    def get(self, path):
        for attempt in range(4):
            if self.requests >= self.budget:
                raise RuntimeError('request budget exhausted')
            self.requests += 1
            req = urllib.request.Request('https://api.github.com/' + path, headers={
                'Authorization': 'Bearer ' + self.token,
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'broccoli-cern-audit'})
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    return json.load(response)
            except urllib.error.HTTPError as exc:
                delay = exc.headers.get('Retry-After', '')
                if exc.code not in (429, 500, 502, 503, 504) and not (exc.code == 403 and delay):
                    raise RuntimeError('GitHub HTTP ' + str(exc.code)) from None
                seconds = int(delay) if delay.isdigit() else 2 ** attempt
                if attempt == 3 or seconds > 60:
                    raise RuntimeError('retry budget exceeded') from None
                time.sleep(seconds)
        raise RuntimeError('unreachable')

    def pages(self, path):
        sep = '&' if '?' in path else '?'
        page = 1
        while True:
            items = self.get(f'{path}{sep}per_page=100&page={page}')
            if not isinstance(items, list):
                raise ValueError('expected a list')
            yield from items
            if len(items) < 100:
                return
            page += 1


def harvest(api, owner, output, include_private=False, repository=None):
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'schema': 1, 'started_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                'owner': owner, 'complete': True, 'repositories': [], 'gaps': [],
                'scope': 'issues/PR titles and labels, branches, commits reachable from current branches; no bodies, comments, diffs or deleted refs'}
    def gap(scope, exc):
        manifest['complete'] = False
        manifest['gaps'].append({'scope': scope, 'error': type(exc).__name__})
    with (output / 'records.jsonl').open('w') as stream:
        def emit(record):
            stream.write(json.dumps(record, ensure_ascii=True) + '\n')
        try:
            path = 'user/repos?affiliation=owner' if include_private else f'users/{owner}/repos?type=owner'
            repos = [api.get('repos/' + repository)] if repository else api.pages(path)
            for repo in repos:
                if repo['owner']['login'].lower() != owner.lower() or repo['fork']:
                    continue
                if repo['private'] and not include_private:
                    continue
                name = repo['full_name']
                manifest['repositories'].append(name)
                root = f'repos/{name}/'
                try:
                    for item in api.pages(root + 'issues?state=all&sort=created&direction=asc'):
                        emit({'repo': name, 'kind': 'pr' if 'pull_request' in item else 'issue',
                              'id': item['number'], 'date': item['created_at'], 'state': item['state'],
                              'bot': (item.get('user') or {}).get('type') == 'Bot',
                              'text': item['title'], 'labels': [x['name'] for x in item['labels']],
                              'url': item['html_url']})
                except (RuntimeError, OSError, ValueError) as exc:
                    gap(name + '/issues', exc)
                try:
                    for branch in api.pages(root + 'branches'):
                        emit({'repo': name, 'kind': 'branch', 'id': branch['name'], 'sha': branch['commit']['sha']})
                        try:
                            for commit in api.pages(root + 'commits?sha=' + urllib.parse.quote(branch['commit']['sha'], safe='')):
                                emit({'repo': name, 'kind': 'commit', 'id': commit['sha'],
                                      'date': commit['commit']['committer']['date'],
                                      'text': commit['commit']['message'].split('\n')[0], 'url': commit['html_url']})
                        except (RuntimeError, OSError, ValueError) as exc:
                            gap(name + '/commits', exc)
                except (RuntimeError, OSError, ValueError) as exc:
                    gap(name + '/branches', exc)
        except (RuntimeError, OSError, ValueError) as exc:
            gap('repository discovery', exc)
    manifest['requests'] = api.requests
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--owner', required=True)
    p.add_argument('--output', type=Path, default=Path('data/cern'))
    p.add_argument('--include-private', action='store_true')
    p.add_argument('--repo', help='Pilot a single owner/repository instead of the ecosystem')
    p.add_argument('--request-budget', type=int, default=2000)
    args = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', args.owner):
        p.error('invalid GitHub owner')
    if args.repo and (not re.fullmatch(r'[A-Za-z0-9-]+/[A-Za-z0-9_.-]+', args.repo) or args.repo.split('/')[0].lower() != args.owner.lower()):
        p.error('--repo must belong to --owner')
    token = os.environ.get('GH_TOKEN')
    if not token:
        p.error('GH_TOKEN is required')
    manifest = harvest(API(token, args.request_budget), args.owner, args.output, args.include_private, args.repo)
    print(json.dumps({'complete': manifest['complete'], 'requests': manifest['requests'], 'gaps': len(manifest['gaps'])}))
    return 0 if manifest['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
