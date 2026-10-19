"""Single-observer information-set MCTS over public action histories.

The tree shares decisions across sampled hidden hands. Availability counts keep
UCT valid when simulated opponent legal actions differ by private hand. Rollout
policies receive only the simulated actor's KnowledgeState. This remains an
approximate decision method, not a Bayesian-equilibrium solver.
"""
from dataclasses import dataclass,field,replace
import math
import random
import time

from domino_engine.knowledge import KnowledgeState,knowledge_for
from domino_engine.rules import apply_move,legal_moves
from domino_engine.strategy import RankedMove
from .belief import BeliefState
from .minimax import LabRanking
from .tactics import score_moves


@dataclass(frozen=True)
class MCTSConfig:
    level: int = 3  # Explicit tree depth; complete-game rollouts evaluate leaves.
    samples: int = 128
    iterations: int = 256
    max_nodes: int = 30000
    time_limit_ms: float = 1500.0
    exploration: float = 1.0
    seed: int = 20261019

    def __post_init__(self):
        for name in ('level','samples','iterations','max_nodes','seed'):
            if type(getattr(self,name)) is not int: raise ValueError(f'{name} must be an integer')
        if not 1<=self.level<=5 or self.samples<1 or self.iterations<1 or self.max_nodes<0:
            raise ValueError('Invalid MCTS tree depth, samples, iterations or node budget')
        if not math.isfinite(self.time_limit_ms) or self.time_limit_ms<=0:
            raise ValueError('Positive finite time budget required')
        if not math.isfinite(self.exploration) or self.exploration<0:
            raise ValueError('Non-negative finite exploration required')


@dataclass
class _Node:
    visits: int = 0
    reward: float = 0.0
    available: int = 0
    children: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MCTSDiagnostics:
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
    tree_depth: int
    iterations_requested: int
    iterations_completed: int
    root_visits: tuple
    # GUI compatibility; ISMCTS does not use alpha-beta or a transposition cache.
    cutoffs: int = 0
    cache_hits: int = 0


class _Limit(Exception): pass


def rollout_move(view,rng):
    """Actor-local policy mixing tactical play and unpredictable legal choices."""
    if not isinstance(view,KnowledgeState): raise TypeError('Rollout policy accepts only KnowledgeState')
    moves = view.legal_moves()
    if len(moves)==1: return moves[0]
    if rng.random()<.12: return rng.choice(moves)
    scores,_ = score_moves(view,exact_blocks=False)
    best = max(scores.values())
    return rng.choice([m for m in moves if scores[m]==best])


class ISMCTSEngine:
    def __init__(self,config=MCTSConfig()):
        self.config = config

    def rank(self,view):
        if not isinstance(view,KnowledgeState): raise TypeError('ISMCTS accepts only KnowledgeState')
        cfg = self.config
        started = time.perf_counter()
        deadline = started+cfg.time_limit_ms/1000
        belief = BeliefState(view)
        priors,notes = score_moves(view)
        moves = view.legal_moves()
        rng = random.Random(cfg.seed)
        worlds = list(belief.worlds(cfg.samples,rng)) if moves else []
        rng.shuffle(worlds)
        root = _Node(children={m:_Node() for m in moves})
        nodes = deepest = completed = 0
        used_worlds = set()
        limit = None

        def step(state,move,ply):
            nonlocal nodes,deepest
            if nodes>=cfg.max_nodes: raise _Limit('nodes')
            if time.perf_counter()>=deadline: raise _Limit('time')
            nodes += 1
            deepest = max(deepest,ply)
            return apply_move(state,move)

        target = min(cfg.iterations,1) if len(moves)==1 else cfg.iterations
        for iteration in range(target if worlds else 0):
            world_index = rng.randrange(len(worlds))
            state = worlds[world_index]
            node,path,ply = root,[root],0
            try:
                while not state.terminal and ply<cfg.level:
                    legal = legal_moves(state)
                    for move in legal:
                        node.children.setdefault(move,_Node()).available += 1
                    unvisited = [m for m in legal if node.children[m].visits==0]
                    if unvisited:
                        # Root ordering is public and shared between worlds.
                        best = max(priors[m] for m in unvisited) if ply==0 else None
                        move = rng.choice([m for m in unvisited if priors[m]==best]) if ply==0 else rng.choice(unvisited)
                    else:
                        sign = 1 if state.turn==view.observer else -1
                        def uct(m):
                            child = node.children[m]
                            return sign*child.reward/child.visits + cfg.exploration*math.sqrt(
                                math.log(max(1,child.available))/child.visits)
                        move = max(legal,key=uct)
                    state = step(state,move,ply+1)
                    ply += 1
                    node = node.children[move]
                    path.append(node)
                    if unvisited: break
                # Full-game simulations are distinct from the explicit tree's
                # 1..5 ply depth. No oracle heuristic reads the sampled enemy hand.
                while not state.terminal and ply<44:
                    move = rollout_move(knowledge_for(state,state.turn),rng)
                    state = step(state,move,ply+1)
                    ply += 1
                if not state.terminal: raise AssertionError('Rollout did not terminate within the rules bound')
            except _Limit as exc:
                limit = str(exc)
                break  # An unfinished simulation contributes NO reward/visits.
            value = .5 if state.winner is None else float(state.winner==view.observer)
            for visited in path:
                visited.visits += 1
                visited.reward += value
            completed += 1
            used_worlds.add(world_index)
        covered = bool(moves) and all(root.children[m].visits for m in moves)
        ranked = []
        for move in moves:
            child = root.children[move]
            # Robust-child recommendation: order by completed visits, a search
            # preference count, explicitly NOT a calibrated probability/utility.
            score = float(child.visits) if covered else priors[move]
            estimate = child.reward/child.visits if child.visits else None
            text = notes[move]+f' ISMCTS: {child.visits} simulazioni complete'
            if estimate is not None: text += f', punti medi simulati {estimate:.3f}'
            text += '; score = visite, non probabilità di vittoria.' if covered else '; ranking euristico di fallback.'
            ranked.append(RankedMove(move,score,priors[move],text))
        ranked.sort(key=lambda r:(-r.score,-r.heuristic_score))
        diag = MCTSDiagnostics(44,44 if covered else 0,deepest,nodes,len(used_worlds),
            (time.perf_counter()-started)*1000,limit is not None,limit,belief.hand_count,
            len(used_worlds)==belief.hand_count,cfg.level,cfg.iterations,completed,
            tuple((str(m),root.children[m].visits) for m in moves))
        return LabRanking(tuple(ranked),diag,belief)


class ISMCTSBot:
    def __init__(self,config=MCTSConfig()):
        self.config = config
        self.last_ranking = None

    def choose(self,view):
        cfg = replace(self.config,seed=self.config.seed+1009*len(view.history)+view.observer.index)
        self.last_ranking = ISMCTSEngine(cfg).rank(view)
        return self.last_ranking.recommendation
