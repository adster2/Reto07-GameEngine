#!/usr/bin/env python3
"""Focused real-browser regression for curved domino placement and persistence."""
import argparse
import json
from pathlib import Path
import time
from playwright.sync_api import sync_playwright
from test_web_browser import tls_transport, stable, propose


def geometry(page):
    return page.evaluate("""() => {
      const layout = pendingVisual?.layout || TableLayout.history(state.view.history, boardPreferences);
      const boxes = layout.tiles.map(TableLayout.rect);
      for (let i=0; i<boxes.length; i++) for(let j=i+1; j<boxes.length; j++) {
        const a=boxes[i], b=boxes[j];
        if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top)
          throw Error('Overlapping dominoes');
      }
      const nodes = [...document.querySelectorAll('#chain .board-tile')];
      const table = document.querySelector('#chain').getBoundingClientRect();
      if(nodes.length !== layout.tiles.length) throw Error('Wrong rendered tile count');
      for(const node of nodes) {
        const box=node.getBoundingClientRect();
        if(box.left < table.left-1 || box.right > table.right+1 || box.top < table.top-1 || box.bottom > table.bottom+1)
          throw Error('Tile outside visible table');
      }
      for(let i=0; i<nodes.length; i++) for(let j=i+1; j<nodes.length; j++) {
        const a=nodes[i].getBoundingClientRect(), b=nodes[j].getBoundingClientRect();
        if(a.left < b.right-.1 && a.right > b.left+.1 && a.top < b.bottom-.1 && a.bottom > b.top+.1)
          throw Error('Rendered dominoes overlap');
      }
      if(document.documentElement.scrollWidth > innerWidth) throw Error('Page overflows viewport');
      const expected = state.view.chain.map(t=>t.join('|'));
      const pending = state.pending;
      if(pending?.legal && !pending.move.pass) {
        if(pending.move.side==='LEFT') expected.unshift(pending.move.orientation.join('|'));
        else expected.push(pending.move.orientation.join('|'));
      }
      if(JSON.stringify(expected)!==JSON.stringify(layout.tiles.map(t=>t.faces.join('|'))))
        throw Error('Layout changed logical face order');
      return {tiles:layout.tiles.length, doubles:layout.tiles.filter(t=>t.double).length,
        directions:layout.tiles.map(t=>t.direction), used:layout.used};
    }""")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8766/')
    parser.add_argument('--output', type=Path, default=Path('local_runs/table-tests'))
    parser.add_argument('--environment-tls', action='store_true')
    parser.add_argument('--cache', type=Path, default=Path('local_runs/web-tests/https-cache'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    errors, tried, checks = [], [], 0
    start = time.perf_counter()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width':1366, 'height':1000}, accept_downloads=True, service_workers='block')
        if args.environment_tls: context.route('https://**/*', tls_transport(args.cache))
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url+'?seed=42&level=3', wait_until='domcontentloaded')
        page.wait_for_selector('body[data-engine-ready="true"]', timeout=90000)
        saved_once, undo_once = False, False
        for _ in range(90):
            data = stable(page)
            geometry(page); checks += 1
            if data['view']['terminal']: break
            if not data['pending']:
                if data['view']['turn'] == 'OPPONENT': page.locator('#cpu-play').click()
                else: propose(page, data)
                continue
            pending = data['pending']
            if not pending['move'].get('pass'):
                unchanged = page.evaluate('JSON.stringify({token:state.token,view:state.view,pending:state.pending})')
                before_preferences = page.evaluate('JSON.stringify(boardPreferences)')
                for direction in ['up', 'down', 'left', 'right']:
                    label = {'up':'l’alto','down':'il basso','left':'sinistra','right':'destra'}[direction]
                    button = page.get_by_role('button', name='Posa verso '+label, exact=True)
                    if button.is_enabled():
                        button.click()
                        assert button.get_attribute('aria-pressed') == 'true'
                        assert page.evaluate('JSON.stringify({token:state.token,view:state.view,pending:state.pending})') == unchanged
                        assert page.evaluate('JSON.stringify(boardPreferences)') == before_preferences
                        geometry(page); checks += 1
                        tried.append(direction)
                # Finish with an available vertical direction whenever possible.
                for direction in ['up', 'down']:
                    label = 'l’alto' if direction == 'up' else 'il basso'
                    button = page.get_by_role('button', name='Posa verso '+label, exact=True)
                    if button.is_enabled(): button.click(); break
                page.screenshot(path=str(args.output/'pending-curve.png'), full_page=True)
            before = data['event_count']
            page.locator('#confirm').click()
            page.wait_for_function('(before)=>state.event_count===before+1 && !busy', arg=before)
            # Pause the next CPU proposal to exercise discard, undo and save/load
            # with actual committed curves, rather than a fabricated board.
            if not saved_once and page.evaluate('state.event_count') >= 4:
                now = stable(page)
                if now['pending']:
                    preferences = page.evaluate('JSON.stringify(boardPreferences)')
                    page.locator('#discard').click()
                    page.wait_for_function('!busy && !state.pending')
                    assert page.evaluate('JSON.stringify(boardPreferences)') == preferences
                original = geometry(page)
                history = page.evaluate('JSON.stringify(state.view.history)')
                page.get_by_text('Salva o riprendi una partita', exact=True).click()
                with page.expect_download() as info: page.locator('#save-game').click()
                saved_path = args.output/'curved-save.json'
                info.value.save_as(str(saved_path))
                saved = json.loads(saved_path.read_text())
                assert saved['table_layout'] == original['used']
                page.locator('#undo').click()
                page.wait_for_function('(count)=>!busy && state.event_count===count-1', arg=before+1)
                geometry(page); undo_once = True
                page.locator('#load-file').set_input_files(str(saved_path))
                page.wait_for_function('(history)=>!busy && JSON.stringify(state.view.history)===history', arg=history)
                assert geometry(page)['used'] == original['used']
                saved_once = True
        else: raise AssertionError('Game did not finish')
        final = stable(page)
        assert final['view']['terminal']
        desktop = geometry(page)
        assert set(tried) == {'up','down','left','right'}
        assert saved_once and undo_once and desktop['doubles'] > 0
        assert len(set(desktop['directions'])) > 1, 'The played chain must actually bend'
        page.screenshot(path=str(args.output/'desktop-curves.png'), full_page=True)
        page.set_viewport_size({'width':375,'height':812})
        page.wait_for_timeout(150)
        mobile = geometry(page)
        assert mobile['used'] == desktop['used'], 'Resizing changed placement choices'
        page.screenshot(path=str(args.output/'mobile-curves.png'), full_page=True)
        # Load old saves with no table metadata; malformed metadata is ignored.
        for metadata in [None, {'0-0':'diagonal','9-9':'up','1-0':'up','2-3':'left'}]:
            assert page.evaluate('(value)=>TableLayout.cleanPreferences(value)', metadata) == ({} if metadata is None else {'2-3':'left'})
            page.evaluate("async (data)=>{cpuPaused=true; await run('load',data);}",
                          {'save':saved['save'], 'level':3, 'table_layout':metadata})
            geometry(page)
        # A new game clears the board preferences without changing the level API.
        page.evaluate("async()=>{cpuPaused=true; await run('new_game',{seed:43,level:3});}")
        page.wait_for_function('!busy && state.event_count===0')
        assert page.evaluate('Object.keys(boardPreferences).length') == 0
        assert not errors, errors
        browser.close()
    report = {'browser':'Chromium', 'seed':42, 'level':3, 'completed_game':True,
        'confirmed_events':final['event_count'], 'geometry_checks':checks, 'directions_tested':sorted(set(tried)),
        'double_tiles':desktop['doubles'], 'save_load':saved_once, 'undo':undo_once,
        'discard_preserves_layout':True, 'direction_preserves_referee':True,
        'mobile_viewport':[375,812], 'page_errors':errors, 'tls_verification_disabled':False,
        'wall_seconds':time.perf_counter()-start}
    (args.output/'TABLE_RESULTS.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__': main()
