#!/usr/bin/env python3
"""Exercise complete games through the same JSON protocol used by the browser."""
import argparse
import csv
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from domino_engine import Player, validate_state
from domino_engine.knowledge import knowledge_for
from domino_engine.simulation import RandomBot
from domino_engine.web_bridge import WebGame


def call(game, command, **data):
    request={'command':command,'token':game.token,**data}
    return json.loads(game.handle_json(json.dumps(request)))


def stress(games, output, seed_start=40000):
    rows=[]
    started=time.perf_counter()
    for index in range(games):
        seed,level=seed_start+index,index%5+1
        game=WebGame(seed,level)
        human=RandomBot(8128)
        nodes=samples=limits=0
        while not game.session.state.terminal:
            assert len(game.session.events)<44,'Deadlock'
            if game.session.state.turn==Player.OPPONENT:
                reply=call(game,'cpu')
                d=reply['cpu_diagnostics']; nodes+=d['nodes']; samples+=d['samples']; limits+=d['budget_exhausted']
            else:
                reply=call(game,'propose',move=human.choose(knowledge_for(game.session.state,Player.ASSISTED)).to_dict())
            assert reply['pending']['legal']
            old=game.session.state
            reply=call(game,'confirm',proposal_id=reply['pending']['id'])
            assert not any(k in reply['view'] for k in ('hands','excluded','seed'))
            assert len(reply['view']['hand'])==len(game.session.state.hand(Player.ASSISTED))
            if game.session.events[-1].move.is_pass:
                assert game.session.state.hands==old.hands
            validate_state(game.session.state)
        saved=call(game,'save')
        restored=WebGame()
        call(restored,'load',**saved)
        assert restored.session.state==game.session.state
        final=game.session.state
        rows.append({'seed':seed,'level':level,'winner':final.winner.value if final.winner else 'DRAW',
                     'reason':final.reason,'plies':len(game.session.events),
                     'passes':sum(e.move.is_pass for e in game.session.events),
                     'nodes':nodes,'samples':samples,'budget_limits':limits,'rule_violations':0,'replay_verified':True})
        if (index+1)%100==0: print(f'{index+1} complete JSON-protocol games',flush=True)
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    summary={'games':games,'seed_start':seed_start,'seed_end':seed_start+games-1,
             'levels':list(range(1,6)),'plies':sum(r['plies'] for r in rows),'rule_violations':0,
             'replays_verified':games,'wall_seconds':time.perf_counter()-started}
    output.with_suffix('.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary),flush=True)
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--games',type=int,default=1000)
    parser.add_argument('--output',type=Path,default=ROOT/'local_runs/web-tests/WEB_STRESS.csv')
    args=parser.parse_args()
    if args.games<1: parser.error('games must be positive')
    stress(args.games,args.output)
