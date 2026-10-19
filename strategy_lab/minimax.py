"""Sampled-hand alpha-beta minimax. Experimental, not a solved Bayesian game.

All root moves use the SAME hypothetical hands. Every simulated opponent reply
minimizes our utility, rather than following the legacy greedy policy. The mean
is computed after solving each world; this determinization still has strategy
fusion/non-locality limitations. It never reads the actual hidden hand.
"""
from dataclasses import dataclass, replace
import math
import random
import statistics
import time

from domino_engine.knowledge import KnowledgeState
from domino_engine.rules import apply_move, legal_moves
from domino_engine.strategy import RankedMove, greedy_key
from .belief import BeliefState
from .heuristic import Weights, public_value, state_value


@dataclass(frozen=True)
class LabConfig:
    level: int = 3
    samples: int = 32
    max_nodes: int = 18000
    time_limit_ms: float = 1500.0
    seed: int = 20261019
    risk: float = 0.0
    weights: Weights = Weights()

    def __post_init__(self):
        if type(self.level) is not int or not 1 <= self.level <= 5:
            raise ValueError('Laboratory level must be 1..5 individual plies')
        if type(self.samples) is not int or self.samples < 1:
            raise ValueError('Positive integer samples required')
        if type(self.max_nodes) is not int or self.max_nodes < 0:
            raise ValueError('Non-negative integer node budget required')
        if not math.isfinite(self.time_limit_ms) or self.time_limit_ms <= 0:
            raise ValueError('Positive finite time budget required')
        if not math.isfinite(self.risk) or not 0 <= self.risk <= 1:
            raise ValueError('Risk penalty must be in [0,1]')
        if not isinstance(self.weights,Weights):
            raise ValueError('Weights must be an immutable Weights configuration')


@dataclass(frozen=True)
class LabDiagnostics:
    requested_depth: int
    completed_depth: int
    deepest_visited: int
    nodes: int
    samples: int
    elapsed_ms: float
    budget_exhausted: bool
    limit: str | None
    possible_hands: int
    exact_belief: bool
    cutoffs: int
    cache_hits: int


@dataclass(frozen=True)
class LabRanking:
    moves: tuple
    diagnostics: LabDiagnostics
    belief: BeliefState

    @property
    def recommendation(self):
        return self.moves[0].move if self.moves else None


class _Limit(Exception):
    pass


class MinimaxEngine:
    def __init__(self, config=LabConfig()):
        self.config = config

    def rank(self, view):
        if not isinstance(view,KnowledgeState):
            raise TypeError('Experimental AI accepts only KnowledgeState')
        started = time.perf_counter()
        cfg = self.config
        deadline = started+cfg.time_limit_ms/1000
        belief = BeliefState(view)
        moves = view.legal_moves()
        baseline = {m:public_value(view,belief,m,cfg.weights) for m in moves}
        scores = dict(baseline)
        nodes = deepest = completed = cutoffs = cache_hits = 0
        limit = None
        worlds = belief.worlds(cfg.samples,random.Random(cfg.seed)) if moves else ()
        cache = {}

        def step(state,move,ply):
            nonlocal nodes,deepest
            if nodes >= cfg.max_nodes:
                raise _Limit('nodes')
            if time.perf_counter() >= deadline:
                raise _Limit('time')
            nodes += 1
            deepest = max(deepest,ply)
            return apply_move(state,move)

        def search(state,remaining,alpha,beta,ply):
            nonlocal cutoffs,cache_hits
            if state.terminal or remaining == 0:
                return state_value(state,view.observer,cfg.weights)
            # Rules depend on hands, free ends, turn and passes, not the drawn
            # geometry/history. Bound flags make reuse under alpha-beta safe.
            key = (state.hands,state.ends,state.turn,state.passes,remaining)
            original_alpha,original_beta = alpha,beta
            cached = cache.get(key)
            if cached:
                cache_hits += 1
                value,flag = cached
                if flag == 'exact': return value
                if flag == 'lower': alpha = max(alpha,value)
                else: beta = min(beta,value)
                if alpha >= beta: return value
            maximize = state.turn == view.observer
            best = -math.inf if maximize else math.inf
            ordered = sorted(legal_moves(state),key=lambda m:greedy_key(state.hand(state.turn),state.chain,m),reverse=True)
            for move in ordered:
                value = search(step(state,move,ply),remaining-1,alpha,beta,ply+1)
                if maximize:
                    best,alpha = max(best,value),max(alpha,value)
                else:
                    best,beta = min(best,value),min(beta,value)
                if alpha >= beta:
                    cutoffs += 1
                    break
            flag = 'upper' if best <= original_alpha else 'lower' if best >= original_beta else 'exact'
            cache[key] = (best,flag)
            return best

        for depth in range(1,cfg.level+1):
            if not worlds: break
            iteration = {}
            try:
                for move in moves:
                    values = [search(step(world,move,1),depth-1,-math.inf,math.inf,2) for world in worlds]
                    iteration[move] = statistics.fmean(values)-cfg.risk*statistics.pstdev(values)
            except _Limit as exc:
                limit = str(exc)
                break
            scores,completed = iteration,depth
        ranked = []
        for move in moves:
            text = ('Passaggio obbligatorio' if move.is_pass else f'Scarica {move.tile.points} punti')
            text += f'; minimax {completed}/{cfg.level} semimosse su {len(worlds)} mani ipotetiche'
            text += '; punteggio di utilità, non probabilità di vittoria.'
            ranked.append(RankedMove(move,scores[move],baseline[move],text))
        ranked.sort(key=lambda r:-r.score)
        diag = LabDiagnostics(cfg.level,completed,deepest,nodes,len(worlds),
            (time.perf_counter()-started)*1000,limit is not None,limit,belief.hand_count,
            len(worlds)==belief.hand_count,cutoffs,cache_hits)
        return LabRanking(tuple(ranked),diag,belief)


class MinimaxBot:
    def __init__(self, config=LabConfig()):
        self.config = config
        self.last_ranking = None

    def choose(self, view):
        cfg = replace(self.config,seed=self.config.seed+1009*len(view.history)+view.observer.index)
        self.last_ranking = MinimaxEngine(cfg).rank(view)
        return self.last_ranking.recommendation
