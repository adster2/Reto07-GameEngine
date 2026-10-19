#!/usr/bin/env python3
"""Build a static Pages site using byte-identical Python modules from this checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MODULES = ('__init__', 'tiles', 'state', 'rules', 'events', 'knowledge', 'strategy',
           'simulation', 'web_bridge')


def build(output):
    output = Path(output).resolve()
    if output == ROOT or output in ROOT.parents or output == ROOT/'web':
        raise ValueError('Output must be a generated directory, not source or checkout root')
    if ROOT in output.parents and ROOT/'local_runs' not in output.parents and output != ROOT/'local_runs':
        raise ValueError('Generated files inside the checkout must stay in local_runs/')
    output.mkdir(parents=True, exist_ok=True)
    for path in (ROOT/'web').iterdir():
        if path.is_file():
            shutil.copyfile(path, output/path.name)
    engine = output/'engine'
    package = engine/'domino_engine'
    package.mkdir(parents=True, exist_ok=True)
    entries = []
    for module in MODULES:
        source = ROOT/'domino_engine'/f'{module}.py'
        target = package/source.name
        shutil.copyfile(source, target)
        entries.append({'path': f'domino_engine/{source.name}',
                        'sha256': hashlib.sha256(source.read_bytes()).hexdigest()})
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    index = output/'index.html'
    html = index.read_text(encoding='utf-8').replace('<head>', '<head>\n  <meta name="reto07-build" content="'+commit+'">')
    html = html.replace('href="style.css"', 'href="style.css?v='+commit+'"').replace('src="app.js"', 'src="app.js?v='+commit+'"')
    index.write_text(html, encoding='utf-8')
    manifest = {'version': 1, 'source_commit': commit,
                'runtime': 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/', 'files': entries}
    (engine/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    (output/'.nojekyll').write_text('')
    (output/'build-info.json').write_text(json.dumps({'source_commit': commit, 'modules': len(entries)}))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'local_runs/site')
    args = parser.parse_args()
    manifest = build(args.output)
    print(f"Static site built: {args.output}; {len(manifest['files'])} original Python modules")
