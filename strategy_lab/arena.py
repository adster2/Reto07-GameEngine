"""Paired, reproducible experiments through the accepted rules and event protocol."""
from concurrent.futures import ProcessPoolExecutor
import csv
from dataclasses import asdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

from domino_engine.events import EventSession
from domino_engine.knowledge import knowledge_for
from domino_engine.simulation import make_bot
from domino_engine.state import Player,deal,validate_state
from .minimax import LabConfig,MinimaxBot
from .ismcts import MCTSConfig,ISMCTSBot


def run_match(seed,opponent='ai3',seat=Player.ASSISTED,first=Player.ASSISTED,config=LabConfig()):
    seat,first = Player(seat),Player(first)
    session = EventSession(deal(seed,first=first))
    lab = ISMCTSBot(config) if isinstance(config,MCTSConfig) else MinimaxBot(config)
    baseline = make_bot(opponent)
    bots = {seat:lab,seat.other:baseline}
    decisions = []
    started = time.perf_counter()
    while not session.state.terminal:
        if len(session.events) >= 44:
            raise AssertionError('Match deadlock')
        actor = session.state.turn
        view = knowledge_for(session.state,actor)
        move = bots[actor].choose(view)
        if move not in view.legal_moves():
            raise AssertionError('Illegal experimental action')
        if actor == seat:
            d = asdict(lab.last_ranking.diagnostics)
            decisions.append({'seed':seed,'opponent':opponent,'seat':seat.value,'first':first.value,
                              'ply':len(session.events),**d})
        proposal = session.propose(move,source='strategy-laboratory')
        session.commit(proposal.id)
        validate_state(session.state)
    journal = session.to_json()
    assert EventSession.from_json(journal).state == session.state, 'Replay mismatch'
    winner = session.state.winner
    row = {'seed':seed,'opponent':opponent,'seat':seat.value,'first':first.value,'level':config.level,
        'algorithm':'ismcts' if isinstance(config,MCTSConfig) else 'minimax',
        'score':.5 if winner is None else float(winner==seat),
        'winner':winner.value if winner else 'DRAW','reason':session.state.reason,
        'plies':len(session.events),'passes':sum(e.move.is_pass for e in session.events),
        'lab_points':sum(t.points for t in session.state.hand(seat)),
        'other_points':sum(t.points for t in session.state.hand(seat.other)),
        'rule_violations':0,'replay_verified':True,
        'nodes':sum(d['nodes'] for d in decisions),'decisions':len(decisions),
        'budget_limits':sum(d['budget_exhausted'] for d in decisions),
        'elapsed_ms':(time.perf_counter()-started)*1000}
    return row,decisions,journal


def _case(payload):
    return run_match(*payload)


def _write_csv(path,rows):
    if not rows: return
    with path.open('w',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def tournament(output,deals=20,seed_start=80000,opponents=('ai3','greedy','random'),config=LabConfig(),workers=1):
    if deals < 1 or not 1 <= workers <= 4:
        raise ValueError('Positive deals and 1..4 workers required')
    # Four combinations per deal, with the same seven tiles and both starters.
    tasks = [(seed,opponent,seat,first,config) for seed in range(seed_start,seed_start+deals)
             for opponent in opponents for seat in Player for first in Player]
    output = Path(output)
    output.mkdir(parents=True,exist_ok=True)
    if (output/'SUMMARY.json').exists():
        raise ValueError('Results already exist: choose a new output directory to preserve evidence')
    rows,decisions = [],[]
    started = time.perf_counter()
    pool = ProcessPoolExecutor(max_workers=workers) if workers > 1 else None
    results = pool.map(_case,tasks,chunksize=1) if pool else map(_case,tasks)
    try:
        with gzip.open(output/'EVENTS.jsonl.gz','wt') as stream:
            for index,(row,ds,journal) in enumerate(results,1):
                rows.append(row); decisions.extend(ds)
                stream.write(json.dumps({'metrics':row,'session':json.loads(journal)},separators=(',',':'))+'\n')
                if index%40 == 0 or index == len(tasks):
                    print(f'Completed {index}/{len(tasks)} laboratory games',flush=True)
    finally:
        if pool: pool.shutdown(cancel_futures=True)
    _write_csv(output/'GAMES.csv',rows)
    _write_csv(output/'DECISIONS.csv',decisions)
    comparisons = []
    for opponent in opponents:
        group = [r for r in rows if r['opponent']==opponent]
        deal_scores = [statistics.mean(r['score'] for r in group if r['seed']==seed)
                       for seed in range(seed_start,seed_start+deals)]
        mean = statistics.mean(deal_scores)
        margin = 1.96*statistics.stdev(deal_scores)/math.sqrt(deals) if deals > 1 else None
        comparisons.append({'opponent':opponent,'games':len(group),'independent_deals':deals,
            'wins':sum(r['score']==1 for r in group),'draws':sum(r['score']==.5 for r in group),
            'losses':sum(r['score']==0 for r in group),'match_points':mean,
            'approx_95ci_by_deal':None if margin is None else [max(0,mean-margin),min(1,mean+margin)]})
    elapsed = sorted(d['elapsed_ms'] for d in decisions)
    summary = {'config':asdict(config),'seed_start':seed_start,'seed_end':seed_start+deals-1,
        'games':len(rows),'plies':sum(r['plies'] for r in rows),'rule_violations':0,
        'replays':len(rows),'decisions':len(decisions),
        'budget_limits':sum(d['budget_exhausted'] for d in decisions),
        'completed_depths':{str(depth):sum(d['completed_depth']==depth for d in decisions)
                            for depth in sorted({d['completed_depth'] for d in decisions})},
        'decision_p95_ms':elapsed[math.ceil(.95*len(elapsed))-1] if elapsed else None,
        'workers':workers,'wall_seconds':time.perf_counter()-started,'comparisons':comparisons,
        'interval_note':'Exploratory normal intervals clustered by deal; no multiple-comparison correction',
        'algorithm':'ismcts' if isinstance(config,MCTSConfig) else 'minimax',
        'limitations':(['SO-ISMCTS is approximate, not a Bayesian equilibrium solver'] if isinstance(config,MCTSConfig)
                      else ['sampled-hand minimax retains strategy fusion'])+
                     ['uniform beliefs do not model voluntary play preferences']}
    _write_csv(output/'COMPARISONS.csv', [{k:v for k,v in r.items() if k!='approx_95ci_by_deal'} for r in comparisons])
    summary['sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in sorted(output.iterdir()) if p.name in ('GAMES.csv','DECISIONS.csv','EVENTS.jsonl.gz','COMPARISONS.csv')}
    (output/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary
