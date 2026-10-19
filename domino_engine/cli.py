"""Command-line simulator, private referee replays, scenarios and measurements."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from .events import EventSession
from .experiments import audit_transcripts, benchmark, stress, tournament
from .scenarios import run_scenario
from .simulation import play_game
from .strategy import SearchConfig


def positive(value):
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError('must be positive')
    return n


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    play = commands.add_parser('play', help='Play complete deterministic bot matches')
    play.add_argument('--seed', type=int, default=42)
    play.add_argument('--games', type=positive, default=1)
    play.add_argument('--assisted', default='ai3')
    play.add_argument('--opponent', default='greedy')
    play.add_argument('--save', type=Path, help='Private referee event log (one game only)')
    play.add_argument('--verbose', action='store_true')
    replay = commands.add_parser('replay')
    replay.add_argument('file', type=Path)
    audit = commands.add_parser('audit')
    audit.add_argument('file', type=Path)
    scenario = commands.add_parser('scenario')
    scenario.add_argument('files', type=Path, nargs='+')
    tour = commands.add_parser('tournament')
    tour.add_argument('--seeds', type=positive, default=50)
    tour.add_argument('--seed-start', type=int, default=10000)
    tour.add_argument('--levels', type=int, nargs='+', choices=range(1, 6), default=[1, 2, 3, 4, 5])
    tour.add_argument('--opponents', nargs='+', choices=['random', 'greedy'], default=['random', 'greedy'])
    tour.add_argument('--output', type=Path, default=Path('local_runs'))
    check = commands.add_parser('stress')
    check.add_argument('--games', type=positive, default=1000)
    check.add_argument('--seed-start', type=int, default=20000)
    check.add_argument('--output', type=Path, default=Path('local_runs/STRESS_RESULTS.csv'))
    bench = commands.add_parser('benchmark')
    bench.add_argument('--positions', type=positive, default=100)
    bench.add_argument('--seed-start', type=int, default=30000)
    bench.add_argument('--output', type=Path, default=Path('local_runs/BENCHMARK_RESULTS.csv'))
    for cmd in (play, tour, bench):
        cmd.add_argument('--samples', type=positive, default=8)
        cmd.add_argument('--max-nodes', type=int, default=6000)
        cmd.add_argument('--time-ms', type=float, default=1500)
        cmd.add_argument('--search-seed', type=int, default=20261019)
    args = parser.parse_args(argv)
    try:
        cfg = SearchConfig(samples=args.samples, max_nodes=args.max_nodes,
                           time_limit_ms=args.time_ms, seed=args.search_seed) if hasattr(args, 'samples') else None
        if args.command == 'play':
            if args.save and args.games != 1:
                parser.error('--save requires --games 1')
            for index in range(args.games):
                run = play_game(args.seed + index, args.assisted, args.opponent, config=cfg)
                if args.verbose:
                    for e in run.session.events:
                        print(e.player.value, str(e.move))
                if args.save:
                    args.save.parent.mkdir(parents=True, exist_ok=True)
                    args.save.write_text(run.session.to_json(), encoding='utf-8')
                print(json.dumps(run.metrics.to_dict()))
        elif args.command == 'replay':
            s = EventSession.from_json(args.file.read_text(encoding='utf-8'))
            print(json.dumps({"events": len(s.events), "terminal": s.state.terminal,
                              "winner": s.state.winner.value if s.state.winner else None,
                              "reason": s.state.reason}))
        elif args.command == 'audit':
            print(json.dumps(audit_transcripts(args.file)))
        elif args.command == 'scenario':
            for file in args.files:
                print(json.dumps(run_scenario(file)))
        elif args.command == 'stress':
            print(json.dumps(stress(args.output, games=args.games, seed_start=args.seed_start,
                                   progress=lambda n: print(f'{n} games completed', file=sys.stderr))))
        elif args.command == 'tournament':
            report = tournament(args.output, seeds=args.seeds, seed_start=args.seed_start,
                                levels=tuple(args.levels), opponents=tuple(args.opponents), config=cfg,
                                progress=lambda group: print(json.dumps(group), flush=True))
            print(json.dumps({"groups": len(report['groups']), "output": str(args.output)}))
        elif args.command == 'benchmark':
            report = benchmark(args.output, positions=args.positions, seed_start=args.seed_start,
                               config=SearchConfig(5, cfg.samples, cfg.max_nodes, cfg.time_limit_ms, cfg.seed))
            args.output.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(report))
        return 0
    except (ValueError, AssertionError, RuntimeError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
