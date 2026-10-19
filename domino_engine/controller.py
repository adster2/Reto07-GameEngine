"""Display-independent GUI controller; safe asynchronous decisions and stale-result rejection."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import random
from .events import EventSession, ObservedScene, ObservedTile, ProposalError
from .knowledge import knowledge_for
from .simulation import make_bot
from .state import Player, deal, from_hands
from .strategy import SearchConfig, StrategyEngine
from .tiles import ALL_TILES


class GameController:
    def __init__(self, seed=42, level=3, opponent=None, session=None):
        self.session = session or EventSession(deal(seed))
        self.level = level
        self.opponent_name = opponent or f"ai{level}"
        self._cpu_follows_level = opponent is None or self.opponent_name.startswith("ai")
        self._opponent_bot = make_bot(self.opponent_name)
        self.ranking = None
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='domino-search')
        self._future = None
        self._token = None
        self._generation = 0
        self.last_diagnostics = None
        self.last_cpu_diagnostics = None
        self.cpu_decisions = 0

    @property
    def busy(self):
        return self._future is not None

    def snapshot(self):
        # The renderer receives no hidden hand or excluded tiles.
        return knowledge_for(self.session.state, Player.ASSISTED)

    def request_decision(self):
        if self.busy or self.session.pending or self.session.state.terminal:
            return False
        view = knowledge_for(self.session.state, self.session.state.turn)
        self._token = (id(self.session), self.session.revision, self.level, self._generation)
        if view.observer == Player.ASSISTED:
            engine = StrategyEngine(SearchConfig(level=self.level,
                        seed=20261019 + 1009 * len(view.history) + view.observer.index))
            self._future = self._pool.submit(engine.rank, view)
        else:
            # Only the filtered view crosses into the persistent fair bot.
            self._future = self._pool.submit(self._opponent_bot.choose, view)
        return True

    def poll_decision(self):
        if self._future is None or not self._future.done():
            return None
        future, token = self._future, self._token
        self._future = None
        expected = (id(self.session), self.session.revision, self.level, self._generation)
        if token != expected or self.session.pending or self.session.state.terminal:
            return 'stale'
        result = future.result()
        if self.session.state.turn == Player.ASSISTED:
            self.ranking = result
            self.last_diagnostics = result.diagnostics
            return 'ranking'
        if hasattr(self._opponent_bot, "last_ranking"):
            self.last_cpu_diagnostics = self._opponent_bot.last_ranking.diagnostics
        self.cpu_decisions += 1
        self.propose_observation(result)
        return 'opponent_proposal'

    def propose_observation(self, move):
        if move.is_pass:
            return self.session.propose(move, source='virtual-pass')
        scene = ObservedScene(tuple(ObservedTile(t.left, t.right) for t in self.session.state.chain)
                              + (ObservedTile(move.tile.a, move.tile.b, move.side, move.orientation),))
        return self.session.observe(scene)

    def reread(self, move):
        p = self.session.pending
        if p is None:
            raise ProposalError('No pending proposal')
        if move.is_pass:
            return self.session.correct(p.id, move)
        scene = ObservedScene(tuple(ObservedTile(t.left, t.right) for t in self.session.state.chain)
                              + (ObservedTile(move.tile.a, move.tile.b, move.side, move.orientation),))
        return self.session.reread(p.id, scene)

    def confirm(self):
        if self.session.pending is None:
            raise ProposalError('No pending proposal')
        self.session.commit(self.session.pending.id)
        self.ranking = None
        self._generation += 1

    def discard(self):
        if self.session.pending:
            self.session.discard(self.session.pending.id)
        self._generation += 1

    def undo(self):
        self.session.undo()
        self.ranking = None
        self._generation += 1

    def replace_session(self, session):
        self.session = session
        self._opponent_bot = make_bot(self.opponent_name)
        self.ranking = None
        self._generation += 1

    def set_level(self, level):
        if level not in range(1, 6):
            raise ValueError('Difficulty must be 1..5')
        self.level = level
        if self._cpu_follows_level:
            self.opponent_name = f"ai{level}"
            self._opponent_bot = make_bot(self.opponent_name)
        self.ranking = None
        self._generation += 1

    def register_manual_hand(self, tiles, *, seed=42, first=Player.ASSISTED):
        tiles = tuple(tiles)
        if len(tiles) != 7 or len(set(tiles)) != 7:
            raise ValueError('Confirm exactly seven different tiles')
        rest = [t for t in ALL_TILES if t not in tiles]
        # This is the virtual referee's deal, independent of strategy sampling.
        rng = random.Random(seed)
        rng.shuffle(rest)
        self.replace_session(EventSession(from_hands(tiles, rest[:7], turn=first, seed=seed)))

    def close(self):
        self._pool.shutdown(wait=True, cancel_futures=True)
