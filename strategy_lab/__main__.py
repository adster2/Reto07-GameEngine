import argparse
from dataclasses import asdict
import json
from pathlib import Path

from domino_engine.events import EventSession
from domino_engine.knowledge import knowledge_for
from domino_engine.state import Player,deal
from .arena import tournament
from .belief import BeliefState
from .minimax import LabConfig,MinimaxEngine
from .ismcts import MCTSConfig,ISMCTSEngine


def config_from_args(args):
    common = dict(level=args.level,time_limit_ms=args.time_ms)
    if args.max_nodes is not None: common['max_nodes'] = args.max_nodes
    if args.samples is not None: common['samples'] = args.samples
    if args.algorithm=='ismcts':
        if args.risk: raise ValueError('--risk applies only to the minimax comparison')
        return MCTSConfig(**common,iterations=args.iterations)
    return LabConfig(**common,risk=args.risk)


def main():
    parser = argparse.ArgumentParser(description='Laboratorio separato: inferenza della mano e ISMCTS')
    sub = parser.add_subparsers(dest='command',required=True)
    for name in ('inspect','rank'):
        p = sub.add_parser(name)
        p.add_argument('--seed',type=int,default=42)
        p.add_argument('--replay',type=Path,help='Journal EventSession o salvataggio del gioco browser')
        p.add_argument('--player',choices=[p.value for p in Player],help='Predefinito: giocatore di turno')
    p = sub.add_parser('arena')
    p.add_argument('--deals',type=int,default=20)
    p.add_argument('--seed-start',type=int,default=80000)
    p.add_argument('--opponents',nargs='+',choices=['ai1','ai2','ai3','ai4','ai5','greedy','random'],default=['ai3','greedy','random'])
    p.add_argument('--workers',type=int,default=1)
    p.add_argument('--output',type=Path,default=Path('local_runs/strategy-lab'))
    for p in sub.choices.values():
        if p.prog.endswith(('rank','arena')):
            p.add_argument('--level',type=int,default=3)
            p.add_argument('--algorithm',choices=['ismcts','minimax'],default='ismcts')
            p.add_argument('--samples',type=int)
            p.add_argument('--iterations',type=int,default=256)
            p.add_argument('--max-nodes',type=int)
            p.add_argument('--time-ms',type=float,default=1500)
            p.add_argument('--risk',type=float,default=0)
    args = parser.parse_args()
    if args.command == 'arena':
        config = config_from_args(args)
        print(json.dumps(tournament(args.output,args.deals,args.seed_start,tuple(args.opponents),config,args.workers),indent=2))
        return
    if args.replay:
        data = json.loads(args.replay.read_text())
        text = data['save'] if data.get('format')=='reto07-browser-v1' else json.dumps(data)
        state = EventSession.from_json(text).state
    else:
        state = deal(args.seed)
    view = knowledge_for(state,Player(args.player) if args.player else state.turn)
    if args.command == 'inspect':
        print(json.dumps(BeliefState(view).to_dict(),indent=2))
    else:
        config = config_from_args(args)
        result = (ISMCTSEngine(config) if isinstance(config,MCTSConfig) else MinimaxEngine(config)).rank(view)
        print(json.dumps({'moves':[m.to_dict() for m in result.moves],'diagnostics':asdict(result.diagnostics),
                          'belief':result.belief.to_dict()},indent=2))


if __name__ == '__main__': main()
