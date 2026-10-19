"""Immutable, non-authoritative information boundary for every fair decision maker."""
from dataclasses import dataclass
import random
from .tiles import ALL_TILES, OrientedTile, Tile
from .state import GameState, Player, PublicEvent, from_hands
from .rules import moves_for


class InconsistentKnowledge(ValueError):
    pass


@dataclass(frozen=True)
class KnowledgeState:
    observer: Player
    hand: tuple[Tile, ...]
    chain: tuple[OrientedTile, ...]
    turn: Player
    opponent_count: int
    history: tuple[PublicEvent, ...]
    passes: int
    terminal: bool
    winner: Player | None
    reason: str | None
    rules: str = "double-six;7-per-player;14-excluded;no-draw;two-passes-block"

    def __post_init__(self):
        if not all(isinstance(x, tuple) for x in (self.hand, self.chain, self.history)):
            raise ValueError("Knowledge collections must be immutable tuples")
        if len(self.hand) > 7:
            raise ValueError("Own hand cannot exceed seven tiles")
        if not 0 <= self.opponent_count <= 7:
            raise ValueError("Invalid opponent count")
        known = [*self.hand, *(t.tile for t in self.chain)]
        if len(known) != len(set(known)):
            raise ValueError("Duplicate known tiles")

    @property
    def ends(self):
        return (self.chain[0].left, self.chain[-1].right) if self.chain else None

    @property
    def unseen(self):
        known = set(self.hand) | {t.tile for t in self.chain}
        return tuple(t for t in ALL_TILES if t not in known)

    @property
    def forbidden_opponent_values(self):
        # With no draws, every tile still held now was also held at each earlier pass.
        # Use the endpoints AT that pass, never today's endpoints retroactively.
        return frozenset(v for e in self.history
                         if e.player == self.observer.other and e.move.is_pass
                         for v in (e.ends_before or ()))

    @property
    def opponent_candidates(self):
        forbidden = self.forbidden_opponent_values
        return tuple(t for t in self.unseen if not forbidden.intersection((t.a, t.b)))

    def legal_moves(self):
        if self.turn != self.observer:
            return ()
        return moves_for(self.hand, self.chain, terminal=self.terminal)

    def to_dict(self):
        return {"observer": self.observer.value, "hand": [t.to_list() for t in self.hand],
                "chain": [t.to_list() for t in self.chain], "turn": self.turn.value,
                "opponent_count": self.opponent_count, "passes": self.passes,
                "history": [e.to_dict() for e in self.history], "terminal": self.terminal,
                "winner": self.winner.value if self.winner else None, "reason": self.reason,
                "rules": self.rules}


def knowledge_for(state: GameState, player: Player):
    """Copy only public facts and the selected player's own hand. No deal seed/RNG."""
    return KnowledgeState(player, tuple(state.hand(player)), tuple(state.chain), state.turn,
                          len(state.hand(player.other)), tuple(state.history), state.passes,
                          state.terminal, state.winner, state.reason)


def sample_world(view: KnowledgeState, rng: random.Random):
    """A hypothetical referee state, sampled without replacement; never real secrets."""
    candidates = view.opponent_candidates
    if len(candidates) < view.opponent_count:
        raise InconsistentKnowledge("Public passes leave too few opponent candidates")
    other = tuple(sorted(rng.sample(candidates, view.opponent_count)))
    hands = (view.hand, other) if view.observer == Player.ASSISTED else (other, view.hand)
    return from_hands(*hands, chain=view.chain, turn=view.turn, passes=view.passes,
                      history=view.history)
