#!/usr/bin/env python3
"""Real Chromium integration tests. Requires the optional playwright dev package.

--environment-tls routes external HTTPS through Python's verified trust store
when the cloud proxy CA is absent from Chromium's NSS store. TLS verification
stays enabled; no browser ignore-certificate flags are used.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
import urllib.request
from playwright.sync_api import sync_playwright


def tls_transport(cache):
    cache.mkdir(parents=True, exist_ok=True)
    def route_request(route):
        url = route.request.url
        key = hashlib.sha256(url.encode()).hexdigest()
        body_path, meta_path = cache/(key+'.bin'), cache/(key+'.json')
        if body_path.exists() and meta_path.exists():
            body, meta = body_path.read_bytes(), json.loads(meta_path.read_text())
        else:
            req = urllib.request.Request(url, headers={'Accept-Encoding':'identity'})
            with urllib.request.urlopen(req, timeout=60) as response:
                body = response.read()
                meta = {'status': response.status, 'headers': dict(response.headers)}
            body_path.write_bytes(body)
            meta_path.write_text(json.dumps(meta))
        headers = {k:v for k,v in meta['headers'].items()
                   if k.lower() not in ('content-length','transfer-encoding','connection')}
        route.fulfill(status=meta['status'], headers=headers, body=body)
    return route_request


def stable(page):
    page.wait_for_function("typeof state !== 'undefined' && state && !busy && (state.pending || state.view.terminal || state.view.turn === 'ASSISTED' || cpuPaused)", timeout=45000)
    if not page.locator('#error').is_hidden():
        raise AssertionError(page.locator('#error').inner_text())
    return page.evaluate('state')


def move_label(move):
    side = 'sinistra' if move['side'] == 'LEFT' else 'destra'
    return f"[{move['tile'][0]}|{move['tile'][1]}] a {side} ({move['orientation'][0]}|{move['orientation'][1]})"


def propose(page, data):
    move = max(data['legal_moves'], key=lambda m: sum(m.get('tile', [-1])))
    if move.get('pass'):
        page.locator('#pass').click()
    else:
        a,b = move['tile']
        page.get_by_role('button', name=f'Gioca tessera {a} e {b}', exact=True).click()
        if page.locator('#placement-dialog').is_visible():
            page.get_by_role('button', name=move_label(move), exact=True).click()
    page.wait_for_function('state.pending && !busy')


def complete_game(page):
    diagnostics = []
    for _ in range(90):
        data = stable(page)
        known = [tuple(sorted(t)) for t in data['view']['hand']+data['view']['chain']]
        assert len(known) == len(set(known)), 'Duplicate visible tile'
        assert not any(k in data['view'] for k in ('hands','excluded','seed'))
        chain = data['view']['chain']
        assert all(a[1] == b[0] for a,b in zip(chain,chain[1:])), 'Broken chain'
        if data['view']['terminal']:
            assert page.locator('#result').is_visible()
            assert data['event_count'] > 0
            assert page.evaluate('window.__heartbeat') > 1
            return data, diagnostics
        assert data['event_count'] < 44, 'Deadlock'
        if data['pending']:
            pending = data['pending']
            assert pending['legal']
            before = data['event_count']
            if pending['player'] == 'OPPONENT':
                diagnostics.append(data['cpu_diagnostics'])
                assert data['cpu_diagnostics']['requested_depth'] == data['level']
                assert data['ranking'] == []
            page.locator('#confirm').click()
            page.wait_for_function('(before) => state.event_count === before+1 && !busy', arg=before)
        elif data['view']['turn'] == 'OPPONENT':
            page.locator('#cpu-play').click()
        else:
            propose(page,data)
    raise AssertionError('Game did not finish')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8765/')
    parser.add_argument('--output', type=Path, default=Path('local_runs/web-tests'))
    parser.add_argument('--environment-tls', action='store_true')
    parser.add_argument('--chromium', default='/usr/bin/chromium')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    errors, results, diagnostics = [], [], []
    started = time.perf_counter()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chromium, headless=True, args=['--no-sandbox'])
        for level in range(1,6):
            context = browser.new_context(viewport={'width':1366,'height':950}, service_workers='block')
            if args.environment_tls: context.route('https://**/*', tls_transport(args.output/'https-cache'))
            page = context.new_page()
            page.add_init_script('window.__heartbeat=0;setInterval(()=>window.__heartbeat++,20);')
            page.on('pageerror',lambda error: errors.append(str(error)))
            page.goto(args.url+f'?seed=42&level={level}', wait_until='domcontentloaded')
            page.wait_for_selector('body[data-engine-ready="true"]', timeout=90000)
            final, ds = complete_game(page)
            diagnostics.extend(ds)
            results.append({'level':level,'events':final['event_count'],'winner':final['view']['winner'],
                            'cpu_decisions':len(ds),'terminal':True})
            page.screenshot(path=str(args.output/f'finished-level-{level}.png'),full_page=True)
            print('Full browser game:',results[-1],flush=True)
            context.close()
        # Mobile controls, actual side dialog, advice, save/load and undo.
        context = browser.new_context(viewport={'width':375,'height':812}, is_mobile=True, has_touch=True,
                                      accept_downloads=True, service_workers='block')
        if args.environment_tls: context.route('https://**/*', tls_transport(args.output/'https-cache'))
        page = context.new_page()
        page.add_init_script('window.__heartbeat=0;setInterval(()=>window.__heartbeat++,20);')
        page.on('pageerror',lambda error: errors.append(str(error)))
        page.goto(args.url+'?seed=43&level=5', wait_until='domcontentloaded')
        page.wait_for_selector('body[data-engine-ready="true"]', timeout=90000)
        data=stable(page)
        assert data['view']['turn']=='ASSISTED'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile layout overflows viewport'
        page.screenshot(path=str(args.output/'mobile.png'),full_page=True)
        page.locator('#show-advice').check()
        page.wait_for_function('state.ranking.length > 0 && !busy')
        assert page.locator('#ranking .rank-row').count()==len(data['legal_moves'])
        page.locator('#show-advice').uncheck()
        assert page.locator('#advice').is_hidden()
        # Save while no move is pending, then restore after making and undoing a move.
        page.get_by_text('Salva o riprendi una partita',exact=True).click()
        with page.expect_download() as download_info:
            page.locator('#save-game').click()
        save_path=args.output/'browser-save.json'
        download_info.value.save_as(str(save_path))
        saved=json.loads(save_path.read_text())
        assert saved['format']=='reto07-browser-v1'
        propose(page,stable(page))
        before=page.evaluate('state.event_count')
        page.locator('#discard').click()
        page.wait_for_function('!busy && !state.pending')
        assert page.evaluate('state.event_count')==before
        propose(page,stable(page))
        page.locator('#confirm').click()
        # The CPU computes a proposal; discard it to make explicit Undo possible.
        page.wait_for_function("state.pending && state.pending.player==='OPPONENT' && !busy")
        page.locator('#discard').click()
        page.wait_for_function('!busy && !state.pending && cpuPaused')
        page.locator('#undo').click()
        page.wait_for_function("!busy && state.event_count===0 && state.view.turn==='ASSISTED'")
        page.locator('#load-file').set_input_files(str(save_path))
        page.wait_for_function('!busy && state.event_count===0')
        assert page.evaluate('state.view.hand')==data['view']['hand']
        # Change level and start again using the actual new-game dialog.
        page.locator('#new-game').click()
        page.locator('#new-level').select_option('2')
        page.locator('#new-dialog details summary').click()
        page.locator('#seed').fill('42')
        page.get_by_role('button',name='Distribuisci le tessere',exact=True).click()
        page.wait_for_function('state.level===2 && !busy')
        final,ds=complete_game(page)
        diagnostics.extend(ds)
        results.append({'mobile':True,'level':2,'events':final['event_count'],'terminal':True,
                        'advice':True,'save_load':True,'discard':True,'undo':True,'new_game':True})
        context.close()
        browser.close()
    assert not errors, errors
    timings=sorted(d['elapsed_ms'] for d in diagnostics)
    report={'url':args.url,'browser':'Chromium','environment_tls':args.environment_tls,
            'tls_verification_disabled':False,'games':results,'page_errors':errors,
            'cpu_decisions':len(diagnostics),'cpu_p95_ms':timings[math.ceil(.95*len(timings))-1],
            'cpu_max_ms':max(timings),'budget_limits':sum(d['budget_exhausted'] for d in diagnostics),
            'wall_seconds':time.perf_counter()-started}
    (args.output/'BROWSER_RESULTS.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    main()
