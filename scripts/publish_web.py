#!/usr/bin/env python3
"""Publish generated static assets to gh-pages, preserving the source checkout.

Run --publish to publish and enable Pages, or --branch-only to prepare the branch
when a repository owner must enable Pages in the GitHub UI. No force pushes.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from build_web import ROOT, build


def git(*args, input=None, env=None):
    return subprocess.check_output(['git', *args], cwd=ROOT, input=input, env=env)


def repository():
    remote = git('remote', 'get-url', 'origin').decode().strip()
    if remote.startswith('git@github.com:'):
        name = remote.split(':',1)[1]
    else:
        parsed = urlsplit(remote)
        if parsed.hostname != 'github.com':
            raise ValueError('Only a GitHub origin is supported')
        name = parsed.path.strip('/')
    name = name.removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', name):
        raise ValueError('Cannot determine repository identity')
    return name


def api(path, *, data=None, allow_missing=False):
    command = ['gh','api',path]
    if data is not None: command += ['--method','POST','--input','-']
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                            input=json.dumps(data) if data is not None else None,
                            env=dict(os.environ, GH_PROMPT_DISABLED='1'))
    try: value = json.loads(result.stdout)
    except ValueError: value = None
    if result.returncode:
        if allow_missing and isinstance(value,dict) and value.get('status') == '404':
            return None
        # Some gh/API versions omit the status member for a missing Pages site.
        if allow_missing and isinstance(value,dict) and value.get('message') == 'Not Found' and 'HTTP 404' in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or 'GitHub API request failed')
    return value


def publish_branch(output):
    remote = git('ls-remote','origin','refs/heads/gh-pages').decode().strip()
    parent = remote.split()[0] if remote else None
    if parent:
        git('fetch','--no-tags','origin','refs/heads/gh-pages')
        try:
            old = json.loads(git('show',f'{parent}:build-info.json'))
            if 'source_commit' not in old: raise ValueError('Unrecognized generated branch')
        except (subprocess.CalledProcessError, ValueError):
            raise RuntimeError('Existing gh-pages branch is not this generated site; preserving it')
    with tempfile.TemporaryDirectory(prefix='reto07-pages-index-') as directory:
        index_env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory)/'index'))
        git('read-tree','--empty',env=index_env)
        lines = []
        for path in sorted(output.rglob('*')):
            if path.is_file():
                oid = git('hash-object','-w','--stdin',input=path.read_bytes()).decode().strip()
                lines.append(f'100644 {oid}\t{path.relative_to(output).as_posix()}\n')
        git('update-index','--index-info',input=''.join(lines).encode(),env=index_env)
        tree = git('write-tree',env=index_env).decode().strip()
        args = ['commit-tree',tree,'-m','Publish browser game from '+git('rev-parse','--short','HEAD').decode().strip()]
        if parent: args += ['-p',parent]
        commit = git(*args).decode().strip()
    git('push','origin',f'{commit}:refs/heads/gh-pages')
    return commit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--publish',action='store_true')
    mode.add_argument('--branch-only',action='store_true')
    args = parser.parse_args()
    output = ROOT/'local_runs/site'
    if git('status','--porcelain','--untracked-files=no').strip():
        raise ValueError('Commit tracked source changes before publishing a reproducible build')
    git('ls-files','--error-unmatch','web/index.html','domino_engine/web_bridge.py')
    manifest = build(output)
    if not (args.publish or args.branch_only):
        print('Site prepared. Use --publish to publish it after reviewing the build.')
        return 0
    repo = repository()
    pages = None
    if args.publish:
        info = api('repos/'+repo)
        pages = api('repos/'+repo+'/pages',allow_missing=True)
        if pages and (pages.get('build_type') == 'workflow' or pages.get('source',{}).get('branch') != 'gh-pages'):
            raise RuntimeError('Pages already has another publishing source; preserving its configuration')
    commit = publish_branch(output)
    if args.publish and pages is None:
        pages = api('repos/'+repo+'/pages',data={'source':{'branch':'gh-pages','path':'/'},'build_type':'legacy'})
    # A configured legacy Pages site builds automatically when gh-pages changes.
    result = {'repository':repo,'source_commit':manifest['source_commit'],'deployed_commit':commit,
              'pages_configured':bool(pages),'url':pages.get('html_url') if pages else None}
    (ROOT/'local_runs/PAGES_DEPLOYMENT.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    try: raise SystemExit(main())
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc),file=sys.stderr)
        raise SystemExit(1)
