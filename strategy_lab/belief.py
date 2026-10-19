"""Uniform beliefs over hidden hands conditioned on public tiles and forced passes.

This is an explicit counting model, not a model of the opponent's preferences.
Unknown tiles can be in the opponent's hand OR permanently outside the game.
"""
from dataclasses import dataclass
from itertools import combinations
from math import comb
import random

from domino_engine.knowledge import KnowledgeState, InconsistentKnowledge
from domino_engine.state import from_hands, Player
from domino_engine.tiles import ALL_TILES, Tile


@dataclass(frozen=True)
class TileBelief:
    tile: Tile
    location: str
    opponent_probability: float
    excluded_probability: float


@dataclass(frozen=True)
class BeliefState:
    view: KnowledgeState

    def __post_init__(self):
        if not isinstance(self.view, KnowledgeState):
            raise TypeError('Beliefs accept only KnowledgeState, never the referee')
        if len(self.candidates) < self.view.opponent_count:
            raise InconsistentKnowledge('Public evidence leaves too few possible opponent tiles')

    @property
    def unseen(self):
        return self.view.unseen

    @property
    def candidates(self):
        return self.view.opponent_candidates if self.view.opponent_count else ()

    @property
    def hand_count(self):
        return comb(len(self.candidates), self.view.opponent_count)

    @property
    def certainly_excluded(self):
        allowed = set(self.candidates)
        return tuple(t for t in self.unseen if t not in allowed)

    def tiles(self):
        hand, public = set(self.view.hand), {t.tile for t in self.view.chain}
        candidates = set(self.candidates)
        probability = self.view.opponent_count / len(candidates) if candidates else 0.0
        return tuple(TileBelief(t,
            'own' if t in hand else 'public' if t in public else
            'candidate' if t in candidates else 'excluded',
            probability if t in candidates else 0.0,
            0.0 if t in hand or t in public else 1.0-probability if t in candidates else 1.0)
            for t in ALL_TILES)

    def pass_probability(self, ends):
        if ends is None:
            return 0.0
        n, k = len(self.candidates), self.view.opponent_count
        misses = sum(not any(t.contains(v) for v in ends) for t in self.candidates)
        return comb(misses, k) / comb(n, k) if misses >= k else 0.0

    def expected_points(self):
        n = len(self.candidates)
        return self.view.opponent_count * sum(t.points for t in self.candidates) / n if n else 0.0

    def hands(self, count, rng: random.Random):
        """Enumerate small beliefs; otherwise draw DISTINCT uniform combinations.

        Unranking avoids materializing up to C(21,7)=116,280 combinations.
        Sampling RNG is supplied by the strategy, independently of the deal.
        """
        if type(count) is not int or count < 1:
            raise ValueError('The number of hypothetical hands must be positive')
        pool, k = self.candidates, self.view.opponent_count
        if self.hand_count <= count:
            return tuple(combinations(pool, k))
        hands = []
        for rank in rng.sample(range(self.hand_count), count):
            chosen, start = [], 0
            for remaining in range(k, 0, -1):
                for index in range(start, len(pool)-remaining+1):
                    block = comb(len(pool)-index-1, remaining-1)
                    if rank < block:
                        chosen.append(pool[index])
                        start = index+1
                        break
                    rank -= block
            hands.append(tuple(chosen))
        return tuple(hands)

    def worlds(self, count, rng):
        v = self.view
        result = []
        for other in self.hands(count, rng):
            hands = (v.hand, other) if v.observer == Player.ASSISTED else (other, v.hand)
            result.append(from_hands(*hands, chain=v.chain, turn=v.turn, passes=v.passes,
                                     history=v.history))
        return tuple(result)

    def to_dict(self):
        return {'model':'uniform-conditioned-on-public-tiles-and-forced-passes',
            'unseen_count':len(self.unseen), 'opponent_count':self.view.opponent_count,
            'expected_excluded_count':len(self.unseen)-self.view.opponent_count,
            'candidate_count':len(self.candidates), 'possible_hands':self.hand_count,
            'forbidden_values':sorted(self.view.forbidden_opponent_values),
            'tiles':[{'tile':t.tile.to_list(), 'location':t.location,
                      'opponent_probability':t.opponent_probability,
                      'excluded_probability':t.excluded_probability} for t in self.tiles()]}
