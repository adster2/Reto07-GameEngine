"""Immutable authoritative state. Never pass this object to a strategy."""
from dataclasses import dataclass
from enum import Enum
import json
import random
from .tiles import ALL_TILES, Move, OrientedTile, Tile


class Player(str, Enum):
    ASSISTED = "ASSISTED"
    OPPONENT = "OPPONENT"

    @property
    def other(self):
        return Player.OPPONENT if self == Player.ASSISTED else Player.ASSISTED

    @property
    def index(self):
        return 0 if self == Player.ASSISTED else 1


@dataclass(frozen=True)
class PublicEvent:
    player: Player
    move: Move
    ends_before: tuple[int, int] | None = None

    def to_dict(self):
        return {"player": self.player.value, "move": self.move.to_dict(),
                "ends_before": list(self.ends_before) if self.ends_before else None}

    @classmethod
    def from_dict(cls, data):
        return cls(Player(data["player"]), Move.from_dict(data["move"]),
                   tuple(data["ends_before"]) if data.get("ends_before") else None)


@dataclass(frozen=True)
class GameState:
    hands: tuple[tuple[Tile, ...], tuple[Tile, ...]]
    excluded: tuple[Tile, ...]
    chain: tuple[OrientedTile, ...]
    turn: Player
    passes: int = 0
    history: tuple[PublicEvent, ...] = ()
    terminal: bool = False
    winner: Player | None = None
    reason: str | None = None
    seed: int | None = None

    def hand(self, player):
        return self.hands[player.index]

    @property
    def ends(self):
        return (self.chain[0].left, self.chain[-1].right) if self.chain else None

    def to_dict(self):
        """Private referee format, NOT an input to StrategyEngine or the camera."""
        return {"version": 1, "hands": [[t.to_list() for t in h] for h in self.hands],
                "excluded": [t.to_list() for t in self.excluded],
                "chain": [t.to_list() for t in self.chain], "turn": self.turn.value,
                "passes": self.passes, "history": [e.to_dict() for e in self.history],
                "terminal": self.terminal, "winner": self.winner.value if self.winner else None,
                "reason": self.reason, "seed": self.seed}

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data):
        if data.get("version") != 1:
            raise ValueError("Unsupported state version")
        state = cls(tuple(tuple(Tile(*t) for t in h) for h in data["hands"]),
                    tuple(Tile(*t) for t in data["excluded"]),
                    tuple(OrientedTile(*t) for t in data["chain"]), Player(data["turn"]),
                    data["passes"], tuple(PublicEvent.from_dict(e) for e in data["history"]),
                    data["terminal"], Player(data["winner"]) if data["winner"] else None,
                    data["reason"], data.get("seed"))
        validate_state(state, check_history=True)
        return state

    @classmethod
    def from_json(cls, text):
        return cls.from_dict(json.loads(text))


def from_hands(assisted, opponent, *, chain=(), turn=Player.ASSISTED,
               passes=0, history=(), seed=None):
    """Controlled scenario/manual setup. Unlisted tiles are excluded, never drawable."""
    hands = (tuple(sorted(assisted)), tuple(sorted(opponent)))
    chain = tuple(chain)
    used = [*hands[0], *hands[1], *(t.tile for t in chain)]
    if len(set(used)) != len(used):
        raise ValueError("Duplicate tile")
    excluded = tuple(t for t in ALL_TILES if t not in used)
    empty = [p for p in Player if not hands[p.index]]
    terminal, winner, reason = False, None, None
    if len(empty) > 1:
        raise ValueError("Both hands cannot be empty")
    if empty:
        terminal, winner, reason = True, empty[0], "empty_hand"
    elif passes == 2:
        terminal, winner, reason = True, blocked_winner(hands), "blocked"
    state = GameState(hands, excluded, chain, Player(turn), passes, tuple(history),
                      terminal, winner, reason, seed)
    validate_state(state)
    return state


def deal(seed=0, *, first=None):
    rng = random.Random(seed)
    tiles = list(ALL_TILES)
    rng.shuffle(tiles)
    turn = Player(first) if first is not None else rng.choice(tuple(Player))
    return from_hands(tiles[:7], tiles[7:14], turn=turn, seed=seed)


def blocked_winner(hands):
    totals = [sum(t.points for t in h) for h in hands]
    if totals[0] == totals[1]:
        return None
    return Player.ASSISTED if totals[0] < totals[1] else Player.OPPONENT


def validate_state(state, *, check_history=False):
    if len(state.hands) != 2 or not isinstance(state.turn, Player):
        raise ValueError("Invalid players")
    if any(len(h) > 7 for h in state.hands) or sum(map(len, state.hands)) + len(state.chain) > 14:
        raise ValueError("More tiles than a no-draw seven-per-player deal permits")
    tiles = [*state.hands[0], *state.hands[1], *state.excluded,
             *(t.tile for t in state.chain)]
    if len(tiles) != 28 or set(tiles) != set(ALL_TILES):
        raise ValueError("Every canonical tile must occur exactly once")
    if any(x.right != y.left for x, y in zip(state.chain, state.chain[1:])):
        raise ValueError("Broken linear chain")
    if type(state.passes) is not int or state.passes not in (0, 1, 2):
        raise ValueError("Invalid consecutive pass count")
    if not state.chain and state.passes:
        raise ValueError("Cannot pass on an empty table")
    if state.passes:
        players = tuple(Player) if state.passes == 2 else (state.turn.other,)
        if any(t.contains(v) for p in players for t in state.hand(p) for v in state.ends):
            raise ValueError("Pass contradicted by a playable tile")
    empty = [p for p in Player if not state.hand(p)]
    if len(empty) > 1:
        raise ValueError("Both hands empty")
    expected_reason = "empty_hand" if empty else "blocked" if state.passes == 2 else None
    expected_winner = empty[0] if empty else blocked_winner(state.hands) if state.passes == 2 else None
    if (state.terminal != (expected_reason is not None) or state.reason != expected_reason
            or state.winner != expected_winner):
        raise ValueError("Inconsistent terminal result")
    if not isinstance(state.history, tuple):
        raise ValueError("History must be immutable")

    if check_history:
        validate_history(state)


def validate_history(state):
    """Reverse a serialized public journal against the private state, without trust.

    Scenario histories may begin after an existing chain; only represented events
    are reversed. Every pre-event hand must be nonempty and every pass forced.
    """
    chain = state.chain
    hands = [list(h) for h in state.hands]
    turn = state.turn
    previous_pass = False
    for index, event in enumerate(state.history):
        if not isinstance(event, PublicEvent):
            raise ValueError("Invalid history event")
        if previous_pass and event.move.is_pass and index != len(state.history)-1:
            raise ValueError("Events after two consecutive passes")
        previous_pass = event.move.is_pass
    for event in reversed(state.history):
        if event.player != turn.other:
            raise ValueError("History turn mismatch")
        move = event.move
        if not move.is_pass:
            if not chain:
                raise ValueError("History placement missing from chain")
            if move.side.value == 'LEFT':
                tile, chain = chain[0], chain[1:]
            else:
                tile, chain = chain[-1], chain[:-1]
            if tile != move.orientation or move.tile in hands[event.player.index]:
                raise ValueError("History tile or orientation mismatch")
            hands[event.player.index].append(move.tile)
        ends = (chain[0].left, chain[-1].right) if chain else None
        if event.ends_before != ends:
            raise ValueError("History endpoints mismatch")
        if any(not hand for hand in hands):
            raise ValueError("History continues after an empty hand")
        if move.is_pass:
            if ends is None or any(t.contains(v) for t in hands[event.player.index] for v in ends):
                raise ValueError("History contains an illegal pass")
        elif chain:
            if (move.side.value == 'LEFT' and move.orientation.right != ends[0]
                    or move.side.value == 'RIGHT' and move.orientation.left != ends[1]):
                raise ValueError("History contains an illegal placement")
        elif move.side.value != 'RIGHT':
            raise ValueError("Noncanonical opening side")
        turn = event.player
