"""Fair expected-value search over sampled worlds with bounded individual plies.

Scores share a utility scale, NOT calibrated win probabilities. Opponent replies use
an explicit greedy policy; own hypothetical replies maximize utility (determinization
approximation, subject to strategy fusion). Never accepts a real GameState.
"""
from dataclasses import dataclass
from math import comb
import random
import time
from .knowledge import KnowledgeState, InconsistentKnowledge, sample_world
from .rules import apply_move, moves_for, place
from .tiles import Move


@dataclass(frozen=True)
class SearchConfig:
    level: int = 3
    samples: int = 8
    max_nodes: int = 6000
    time_limit_ms: float = 1500.0
    seed: int = 20261019

    def __post_init__(self):
        if type(self.level) is not int or self.level not in range(1, 6):
            raise ValueError("Difficulty must be 1..5 individual plies")
        if self.samples < 1 or self.max_nodes < 0 or self.time_limit_ms <= 0:
            raise ValueError("Invalid search budget")


@dataclass(frozen=True)
class RankedMove:
    move: Move
    score: float
    heuristic_score: float
    explanation: str

    def to_dict(self):
        return {"move": self.move.to_dict(), "score": self.score,
                "heuristic_score": self.heuristic_score, "explanation": self.explanation}


@dataclass(frozen=True)
class SearchDiagnostics:
    requested_depth: int
    completed_depth: int
    deepest_visited: int
    nodes: int
    samples: int
    elapsed_ms: float
    budget_exhausted: bool
    limit: str | None


@dataclass(frozen=True)
class Ranking:
    moves: tuple[RankedMove, ...]
    diagnostics: SearchDiagnostics

    @property
    def recommendation(self):
        return self.moves[0].move if self.moves else None


class _BudgetReached(Exception):
    pass


def _mobility(hand, chain):
    if not chain:
        return len(hand)
    ends = (chain[0].left, chain[-1].right)
    return sum(any(t.contains(v) for v in ends) for t in hand)


def _features(hand, chain):
    diversity = len({v for t in hand for v in (t.a, t.b)})
    stranded = sum(t.points for t in hand if t.a == t.b and
                   not any(t.contains(v) for v in (chain[0].left, chain[-1].right))) if chain else 0
    return diversity, stranded


def _utility(own, chain, opponent_count, opponent_points, opponent_mobility):
    diversity, stranded = _features(own, chain)
    return (8.0 * (opponent_count - len(own))
            + 1.3 * (opponent_points - sum(t.points for t in own))
            + 2.5 * (_mobility(own, chain) - opponent_mobility)
            + 0.6 * diversity - 0.8 * stranded)


def _state_value(state, observer):
    if state.terminal:
        return 0.0 if state.winner is None else 1000.0 if state.winner == observer else -1000.0
    other = state.hand(observer.other)
    return max(-500.0, min(500.0, _utility(
        state.hand(observer), state.chain, len(other), sum(t.points for t in other),
        _mobility(other, state.chain))))


def greedy_key(hand, chain, move):
    """Public baseline: shed most pips, then retain mobility. No hidden information."""
    if move.is_pass:
        return (-1, 0)
    remaining = tuple(t for t in hand if t != move.tile)
    return (move.tile.points, _mobility(remaining, place(chain, move)))


def _heuristic(view, move):
    hand = view.hand if move.is_pass else tuple(t for t in view.hand if t != move.tile)
    chain = place(view.chain, move)
    if not hand:
        return 1000.0
    if move.is_pass and view.passes == 1:
        # Expected terminal result under the same public-conditioned distribution.
        return None
    candidates = tuple(t for t in view.opponent_candidates if t != move.tile)
    n, k = len(candidates), view.opponent_count
    if k > n:
        raise InconsistentKnowledge("Insufficient unseen opponent candidates")
    avg = sum(t.points for t in candidates) / n if n else 0
    hits = sum(t.contains(chain[0].left) or t.contains(chain[-1].right) for t in candidates)
    block_prob = comb(n - hits, k) / comb(n, k) if k <= n - hits and n else 0.0
    return max(-500.0, min(500.0, _utility(hand, chain, k, k * avg, k * hits / n if n else 0)
                              + 8.0 * block_prob))


class StrategyEngine:
    def __init__(self, config=SearchConfig()):
        self.config = config

    def rank(self, view: KnowledgeState):
        if not isinstance(view, KnowledgeState):
            raise TypeError("StrategyEngine accepts only KnowledgeState")
        cfg = self.config
        started = time.perf_counter()
        deadline = started + cfg.time_limit_ms / 1000.0
        moves = view.legal_moves()
        if not moves:
            return Ranking((), SearchDiagnostics(cfg.level, 0, 0, 0, 0, 0.0, False, None))
        nodes, deepest, completed, samples_used, limit = 0, 1, 1, 0, None
        rng = random.Random(cfg.seed)  # Never shared with deal or simulation RNG.
        worlds = []
        try:
            worlds = [sample_world(view, rng) for _ in range(cfg.samples)] if cfg.level > 1 or (
                moves[0].is_pass and view.passes == 1) else []
            samples_used = len(worlds)
            baseline = {}
            for m in moves:
                value = _heuristic(view, m)
                if value is None:
                    value = sum(_state_value(apply_move(s, m), view.observer) for s in worlds) / len(worlds)
                baseline[m] = value
        except InconsistentKnowledge:
            # Invalid public knowledge is explicit; still return every legal action.
            baseline = {m: (1000.0 if len(view.hand) == 1 and not m.is_pass else
                            float(0 if m.is_pass else m.tile.points)) for m in moves}
            worlds, limit = [], "inconsistent_knowledge"
        scores = dict(baseline)

        def step(state, move, ply):
            nonlocal nodes, deepest
            if nodes >= cfg.max_nodes:
                raise _BudgetReached("nodes")
            if time.perf_counter() >= deadline:
                raise _BudgetReached("time")
            nodes += 1
            deepest = max(deepest, ply)
            return apply_move(state, move)

        def search(state, remaining, ply):
            if remaining == 0 or state.terminal:
                return _state_value(state, view.observer)
            legal = moves_for(state.hand(state.turn), state.chain)
            if state.turn != view.observer:
                # Plausible policy conditioned on the hypothetical hand only.
                reply = max(legal, key=lambda m: greedy_key(state.hand(state.turn), state.chain, m))
                return search(step(state, reply, ply), remaining - 1, ply + 1)
            return max(search(step(state, m, ply), remaining - 1, ply + 1) for m in legal)

        if worlds and limit is None:
            for depth in range(2, cfg.level + 1):
                iteration = {}
                try:
                    for move in moves:
                        iteration[move] = sum(search(step(s, move, 1), depth - 1, 2)
                                              for s in worlds) / len(worlds)
                except _BudgetReached as exc:
                    limit = str(exc)
                    break
                scores, completed = iteration, depth
        explanation_depth = f"ricerca {completed}/{cfg.level} semimosse"
        ranked = []
        for move in moves:
            if move.is_pass:
                text = f"Passaggio obbligatorio; {explanation_depth}."
            else:
                chain = place(view.chain, move)
                text = (f"Scarica {move.tile.points} punti; estremi {chain[0].left}/{chain[-1].right}; "
                        f"mobilità residua {_mobility(tuple(t for t in view.hand if t != move.tile), chain)}; "
                        f"{explanation_depth}.")
            ranked.append(RankedMove(move, scores[move], baseline[move], text))
        ranked.sort(key=lambda r: -r.score)  # stable canonical tie-break, no secret RNG
        elapsed = (time.perf_counter() - started) * 1000
        return Ranking(tuple(ranked), SearchDiagnostics(cfg.level, completed, deepest, nodes,
                       samples_used, elapsed, limit is not None, limit))
