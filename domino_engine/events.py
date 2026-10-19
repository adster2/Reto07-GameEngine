"""Camera-neutral observation -> proposal -> explicit atomic commit protocol."""
from collections import Counter
from dataclasses import dataclass, replace
import json
from threading import RLock
from .tiles import Move, OrientedTile, Side, Tile
from .state import GameState, Player
from .rules import IllegalMove, apply_move


class ProposalError(ValueError):
    pass


@dataclass(frozen=True)
class ObservedTile:
    a: int
    b: int
    side: Side = Side.RIGHT
    orientation: OrientedTile | None = None
    confidence: float = 1.0

    def to_move(self):
        return Move(Tile(self.a, self.b), self.side,
                    self.orientation or OrientedTile(self.a, self.b))


@dataclass(frozen=True)
class ObservedScene:
    """Full table snapshot. Coordinates/pixels belong to the external adapter."""
    tiles: tuple[ObservedTile, ...]
    geometry_ambiguous: bool = False
    image_ref: str | None = None


@dataclass(frozen=True)
class MoveProposal:
    id: str
    revision: int
    player: Player
    move: Move
    legal: bool
    error: str | None
    new_ends: tuple[int, int] | None
    source: str = "manual"
    image_ref: str | None = None


# Public alias for adapters using the name in the specification.
ProposedMove = MoveProposal


@dataclass(frozen=True)
class CommittedEvent:
    id: str
    player: Player
    move: Move

    def to_dict(self):
        return {"id": self.id, "player": self.player.value, "move": self.move.to_dict()}


class EventSession:
    """Only confirmed events change state. The lock also protects concurrent commits."""
    def __init__(self, initial: GameState):
        # Strict roundtrip validates supplied initial state, including tile accounting.
        self.initial = GameState.from_dict(initial.to_dict())
        self._state = self.initial
        self._events = []
        self._pending = None
        self._revision = 0
        self._serial = 0
        self._revoked = set()
        self._lock = RLock()
        self.last_observation_error = None

    @property
    def state(self):
        with self._lock:
            return self._state

    @property
    def pending(self):
        with self._lock:
            return self._pending

    @property
    def events(self):
        with self._lock:
            return tuple(self._events)

    @property
    def revision(self):
        with self._lock:
            return self._revision

    def _make(self, id, move, source, image_ref):
        try:
            future = apply_move(self.state, move)
            legal, error, ends = True, None, future.ends
        except (ValueError, TypeError) as exc:
            legal, error, ends = False, str(exc), None
        return MoveProposal(id, self.revision, self.state.turn, move, legal,
                            error, ends, source, image_ref)

    def propose(self, move, *, source="manual", image_ref=None):
        with self._lock:
            if self.pending is not None:
                raise ProposalError("Resolve the pending proposal first")
            self._serial += 1
            used_ids = {e.id for e in self._events} | self._revoked
            while f"move-{self._serial}" in used_ids:
                self._serial += 1
            self._pending = self._make(f"move-{self._serial}", move, source, image_ref)
            return self.pending

    def correct(self, id, move):
        with self._lock:
            self._require_pending(id)
            self._pending = self._make(id, move, "correction", self.pending.image_ref)
            return self.pending

    def _require_pending(self, id):
        if self.pending is None or self.pending.id != id:
            raise ProposalError("No matching pending proposal")

    def discard(self, id):
        with self._lock:
            self._require_pending(id)
            self._pending = None

    def _scene_move(self, scene):
        if scene.geometry_ambiguous:
            raise ProposalError("Ambiguous geometry: correct or acquire another scene")
        baseline = Counter(t.tile for t in self.state.chain)
        observed = Counter(Tile(t.a, t.b) for t in scene.tiles)
        if baseline - observed:
            raise ProposalError("Confirmed tiles missing or misread; acquire another scene")
        additions = observed - baseline
        if sum(additions.values()) != 1:
            raise ProposalError("Exactly one new tile is required")
        tile = next(iter(additions))
        if tile in baseline or observed[tile] != 1:
            raise ProposalError("Duplicate tile in observation")
        detection = next(t for t in scene.tiles if Tile(t.a, t.b) == tile)
        if not 0.8 <= detection.confidence <= 1.0:
            raise ProposalError("Low confidence: correct or acquire another scene")
        return detection.to_move()

    def observe(self, scene):
        with self._lock:
            if self.pending is not None:
                raise ProposalError("Resolve the pending proposal first")
            try:
                move = self._scene_move(scene)
                self.last_observation_error = None
            except ValueError as exc:
                self.last_observation_error = str(exc)
                return None
            return self.propose(move, source="observation", image_ref=scene.image_ref)

    def reread(self, id, scene):
        with self._lock:
            self._require_pending(id)
            # Compare with CONFIRMED state, never with the last raw observation.
            try:
                move = self._scene_move(scene)
                self.last_observation_error = None
            except ValueError as exc:
                self.last_observation_error = str(exc)
                # An ambiguous reread must not leave an older proposal confirmable.
                self._pending = replace(self.pending, legal=False, error=str(exc))
                return None
            self._pending = self._make(id, move, "reread", scene.image_ref)
            return self.pending

    def commit(self, id):
        with self._lock:
            if id in self._revoked:
                raise ProposalError("This event was undone")
            if any(e.id == id for e in self._events):
                return self.state  # idempotency: no second transition
            self._require_pending(id)
            proposal = self.pending
            if proposal.revision != self.revision or proposal.player != self.state.turn:
                raise ProposalError("Stale proposal")
            if not proposal.legal:
                raise IllegalMove(proposal.error)
            # Revalidate before publishing state and event together.
            future = apply_move(self.state, proposal.move, player=proposal.player)
            self._events.append(CommittedEvent(id, proposal.player, proposal.move))
            self._state = future
            self._revision += 1
            self._pending = None
            return self.state

    def undo(self):
        with self._lock:
            if self.pending is not None:
                raise ProposalError("Discard the pending proposal before undo")
            if not self._events:
                raise ProposalError("No committed event to undo")
            remaining = self._events[:-1]
            future = self.initial
            for event in remaining:
                future = apply_move(future, event.move, player=event.player)
            self._revoked.add(self._events[-1].id)
            self._events = remaining
            self._state = future
            self._revision += 1
            return future

    def to_dict(self):
        with self._lock:
            return {"version": 1, "initial": self.initial.to_dict(),
                    "events": [e.to_dict() for e in self.events],
                    "final": self.state.to_dict(), "serial": self._serial}

    def to_json(self):
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, text):
        data = json.loads(text)
        if data.get("version") != 1:
            raise ProposalError("Unsupported event log version")
        session = cls(GameState.from_dict(data["initial"]))
        seen = set()
        for e in data["events"]:
            if not isinstance(e["id"], str) or not e["id"] or e["id"] in seen:
                raise ProposalError("Duplicate or invalid event id")
            seen.add(e["id"])
            player, move = Player(e["player"]), Move.from_dict(e["move"])
            session._state = apply_move(session.state, move, player=player)
            session._events.append(CommittedEvent(e["id"], player, move))
        if session.state != GameState.from_dict(data["final"]):
            raise ProposalError("Replay does not match saved final state")
        session._serial = max(int(data["serial"]), len(seen))
        # Avoid reusing any loaded arbitrary event id.
        while f"move-{session._serial + 1}" in seen:
            session._serial += 1
        session._revision = len(seen)
        return session
