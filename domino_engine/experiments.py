"""Reproducible paired tournaments, independent evaluation and latency benchmarks."""
from dataclasses import asdict
import csv
import gzip
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
from .knowledge import knowledge_for
from .simulation import play_game
from .state import Player, deal
from .strategy import SearchConfig, StrategyEngine
from .rules import legal_moves


def machine_info():
    model = platform.processor()
    if not model and Path('/proc/cpuinfo').exists():
        model = next((line.split(':', 1)[1].strip() for line in
                      Path('/proc/cpuinfo').read_text().splitlines()
                      if line.startswith('model name')), 'unreported')
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else os.cpu_count()
    return {"python": sys.version, "platform": platform.platform(),
            "processor": model, "available_cpus": cpus}


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError('No results to write')
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def tournament(output, *, seeds=50, seed_start=10000, levels=(1, 2, 3, 4, 5),
               opponents=('random', 'greedy'), config=SearchConfig(), progress=None):
    """Four games per deal: AI in both seats and both starting players.

    Seeds/deals are the units of uncertainty. CI uses per-seed paired scores, since
    the four games sharing a deal are not independent Bernoulli observations.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows, decision_rows, summaries = [], [], []
    transcript = output / "TOURNAMENT_EVENTS.jsonl.gz"
    transcript.write_bytes(b"")
    for level in levels:
        for opponent in opponents:
            group, seed_scores = [], []
            for seed in range(seed_start, seed_start + seeds):
                pair = []
                for seat in Player:
                    for first in Player:
                        assisted, other = (f'ai{level}', opponent) if seat == Player.ASSISTED else (opponent, f'ai{level}')
                        run = play_game(seed, assisted, other, first=first, config=config)
                        m = run.metrics
                        score = 0.5 if m.winner is None else float(m.winner == seat.value)
                        row = {"level": level, "opponent": opponent, "ai_seat": seat.value,
                               "score": score, **m.to_dict()}
                        group.append(row)
                        rows.append(row)
                        # One gzip member per game permits recovery of complete earlier games.
                        record = {"game_index": len(rows)-1, "level": level, "opponent": opponent,
                                  "ai_seat": seat.value, "seed": seed, "first": first.value,
                                  "events": [e.to_dict() for e in run.session.events],
                                  "final": run.session.state.to_dict()}
                        with transcript.open('ab') as raw:
                            with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as zipped:
                                zipped.write((json.dumps(record, separators=(',', ':'))+'\n').encode())
                        pair.append(score)
                        decision_rows.extend({"level": level, "opponent": opponent,
                                              "ai_seat": seat.value, "first": first.value, **d}
                                             for d in run.decisions)
                seed_scores.append(statistics.mean(pair))
            n = len(group)
            mean = statistics.mean(seed_scores)
            margin = 1.96 * statistics.stdev(seed_scores) / math.sqrt(seeds) if seeds > 1 else None
            summaries.append({"level": level, "opponent": opponent, "games": n,
                              "independent_deals": seeds,
                              "wins": sum(r['score'] == 1 for r in group),
                              "draws": sum(r['score'] == .5 for r in group),
                              "losses": sum(r['score'] == 0 for r in group),
                              "score_rate": mean,
                              "approx_95_ci_deal_cluster": [max(0, mean-margin), min(1, mean+margin)] if margin is not None else None,
                              "rule_violations": sum(r['rule_violations'] for r in group),
                              "mean_plies": statistics.mean(r['plies'] for r in group),
                              "elapsed_ms": sum(r['elapsed_ms'] for r in group)})
            # Save each complete group; interrupted runs preserve completed evidence.
            write_csv(output / 'TOURNAMENT_RESULTS.csv', rows)
            write_csv(output / 'TOURNAMENT_DECISIONS.csv', decision_rows)
            report = {"machine": machine_info(), "search_config": asdict(config),
                      "seed_start": seed_start, "seed_count": seeds,
                      "groups": summaries}
            (output / 'TOURNAMENT_SUMMARY.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            if progress:
                progress(summaries[-1])
    return report


def stress(output, *, games=1000, seed_start=20000, progress=None):
    rows = []
    for index in range(games):
        a, b = (('random', 'greedy'), ('greedy', 'random'), ('random', 'random'))[index % 3]
        run = play_game(seed_start + index, a, b)
        # Full replay through the same validators, not just terminal flag/PID checks.
        from .events import EventSession
        restored = EventSession.from_json(run.session.to_json())
        if restored.state != run.session.state:
            raise AssertionError('Replay mismatch')
        rows.append(run.metrics.to_dict())
        if progress and (index + 1) % 250 == 0:
            progress(index + 1)
    write_csv(output, rows)
    return {"games": games, "seed_start": seed_start, "seed_end": seed_start + games - 1,
            "completed": len(rows), "rule_violations": 0,
            "plies": sum(r['plies'] for r in rows), "replays_verified": len(rows)}


def benchmark(output, *, positions=100, seed_start=30000, config=SearchConfig(level=5)):
    rows = []
    # Opening, middle and late positions from fair random/greedy games, independent
    # of development and tournament seeds. Do NOT select positions by runtime.
    for index in range(positions):
        run = play_game(seed_start + index, 'random', 'greedy')
        state = run.session.initial
        from .rules import apply_move
        prefix = (0, len(run.session.events) // 2, max(0, len(run.session.events) - 2))[index % 3]
        for event in run.session.events[:prefix]:
            state = apply_move(state, event.move)
        view = knowledge_for(state, state.turn)
        ranking = StrategyEngine(config).rank(view)
        if set(x.move for x in ranking.moves) != set(legal_moves(state)):
            raise AssertionError('Incomplete benchmark ranking')
        rows.append({"position": index, "seed": seed_start + index, "prefix_plies": prefix,
                     "legal_moves": len(ranking.moves), **asdict(ranking.diagnostics)})
    write_csv(output, rows)
    elapsed = sorted(r['elapsed_ms'] for r in rows)
    p95 = elapsed[max(0, math.ceil(.95 * len(elapsed)) - 1)]
    return {"machine": machine_info(), "search_config": asdict(config),
            "positions": positions, "seed_start": seed_start,
            "p95_ms": p95, "max_ms": max(elapsed), "mean_ms": statistics.mean(elapsed),
            "within_5s_rate": sum(x <= 5000 for x in elapsed) / len(elapsed),
            "latency_gate_pass": p95 <= 5000,
            "depth5_completed": sum(r['completed_depth'] == 5 for r in rows),
            "budget_limits": sum(r['budget_exhausted'] for r in rows)}


def audit_transcripts(path):
    """Replay every saved tournament event against the declared seeded deal."""
    from .state import GameState
    from .rules import apply_move
    from .tiles import Move
    games = plies = 0
    seeds = set()
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        for line in stream:
            record = json.loads(line)
            if record['game_index'] != games:
                raise ValueError('Transcript index missing or repeated')
            state = deal(record['seed'], first=Player(record['first']))
            ids = set()
            for event in record['events']:
                if event['id'] in ids:
                    raise ValueError('Duplicate transcript event id')
                ids.add(event['id'])
                state = apply_move(state, Move.from_dict(event['move']), player=Player(event['player']))
                plies += 1
            if not state.terminal or state != GameState.from_dict(record['final']):
                raise ValueError('Transcript final state mismatch')
            seeds.add(record['seed'])
            games += 1
    if not games:
        raise ValueError('No tournament games audited')
    return {"games": games, "plies": plies, "distinct_deals": len(seeds),
            "rule_violations": 0, "all_terminal": True, "replays_verified": games}
