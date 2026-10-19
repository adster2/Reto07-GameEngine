"""Independently replay and reconcile a saved laboratory tournament."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

from domino_engine.events import EventSession
from domino_engine.state import Player


def audit(directory):
    directory = Path(directory)
    summary = json.loads((directory/'SUMMARY.json').read_text())
    for name,expected in summary['sha256'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=expected:
            raise AssertionError('Evidence hash mismatch: '+name)
    with (directory/'GAMES.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    def key(row): return (int(row['seed']),row['opponent'],row['seat'],row['first'])
    games = {key(row):row for row in rows}
    assert len(games)==len(rows)==summary['games'], 'Duplicate or missing games'
    opponents = {row['opponent'] for row in rows}
    expected = {(seed,opponent,seat.value,first.value)
                for seed in range(summary['seed_start'],summary['seed_end']+1)
                for opponent in opponents for seat in Player for first in Player}
    assert set(games)==expected, 'Unbalanced deals/seats/starters'
    seen,plies = set(),0
    with gzip.open(directory/'EVENTS.jsonl.gz','rt') as stream:
        for line in stream:
            record = json.loads(line)
            metrics = record['metrics']
            k = key(metrics)
            assert k in games and k not in seen, 'Duplicate or unlisted transcript'
            seen.add(k)
            row = games[k]
            session = EventSession.from_json(json.dumps(record['session']))
            state = session.state
            assert state.terminal and len(session.events)==int(row['plies'])
            assert (state.winner.value if state.winner else 'DRAW')==row['winner']
            seat = Player(row['seat'])
            score = .5 if state.winner is None else float(state.winner==seat)
            assert score==float(row['score'])==float(metrics['score'])
            assert sum(t.points for t in state.hand(seat))==int(row['lab_points'])
            assert sum(t.points for t in state.hand(seat.other))==int(row['other_points'])
            assert sum(e.move.is_pass for e in session.events)==int(row['passes'])
            assert int(row['rule_violations'])==0
            plies += len(session.events)
    assert seen==set(games) and plies==summary['plies']
    decision_totals = {k:[0,0,0] for k in games}
    with (directory/'DECISIONS.csv').open(newline='') as stream:
        for d in csv.DictReader(stream):
            counts = decision_totals[key(d)]
            counts[0] += 1; counts[1] += int(d['nodes']); counts[2] += d['budget_exhausted']=='True'
    for k,row in games.items():
        assert decision_totals[k]==[int(row[n]) for n in ('decisions','nodes','budget_limits')]
    result = {'games':len(rows),'plies':plies,'replays_verified':len(seen),
              'balanced_cases':True,'hashes_verified':True,'decision_rows_reconciled':True,
              'rule_violations':0}
    (directory/'AUDIT.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    print(json.dumps(audit(parser.parse_args().directory),indent=2))
