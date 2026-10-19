"""Referee and fair bots. Bots receive only an immutable KnowledgeState."""
from dataclasses import asdict, dataclass, replace
import random
import time
from .events import EventSession
from .knowledge import knowledge_for
from .state import Player, deal, validate_state
from .strategy import Ranking, SearchConfig, StrategyEngine, greedy_key


class RandomBot:
    def __init__(self, seed=8128):
        self.rng = random.Random(seed)  # Independent of deal RNG/seed.

    def choose(self, view):
        return self.rng.choice(view.legal_moves())


class GreedyBot:
    def choose(self, view):
        return max(view.legal_moves(), key=lambda m: greedy_key(view.hand, view.chain, m))


class StrategyBot:
    def __init__(self, config=SearchConfig()):
        self.config = config
        self.last_ranking = None

    def choose(self, view):
        cfg = replace(self.config, seed=self.config.seed + 1009 * len(view.history) + view.observer.index)
        self.last_ranking = StrategyEngine(cfg).rank(view)
        return self.last_ranking.recommendation


def make_bot(name, *, config=None):
    if name == 'random':
        return RandomBot()
    if name == 'greedy':
        return GreedyBot()
    if name.startswith('ai') and name[2:] in ('1', '2', '3', '4', '5'):
        return StrategyBot(replace(config or SearchConfig(), level=int(name[2:])))
    raise ValueError(f"Unknown bot: {name}")


@dataclass(frozen=True)
class GameMetrics:
    seed: int
    first: str
    assisted_bot: str
    opponent_bot: str
    winner: str | None
    reason: str
    plies: int
    passes: int
    assisted_points: int
    opponent_points: int
    rule_violations: int
    elapsed_ms: float
    nodes: int
    samples: int
    decisions: int
    budget_limits: int

    def to_dict(self):
        return asdict(self)


@dataclass
class GameRun:
    session: EventSession
    metrics: GameMetrics
    decisions: list[dict]


def play_game(seed, assisted='ai3', opponent='greedy', *, first=None,
              config=None, initial=None):
    state = initial or deal(seed, first=first)
    session = EventSession(state)
    bots = {Player.ASSISTED: make_bot(assisted, config=config),
            Player.OPPONENT: make_bot(opponent, config=config)}
    first_player = state.turn
    decisions = []
    nodes = samples = budget_limits = 0
    started = time.perf_counter()
    while not session.state.terminal:
        if len(session.events) >= 44:
            raise RuntimeError('Deadlock: more than the maximum 14 placements + forced passes')
        player = session.state.turn
        bot = bots[player]
        view = knowledge_for(session.state, player)
        move = bot.choose(view)  # The only data flowing into a bot.
        if isinstance(bot, StrategyBot):
            diag = bot.last_ranking.diagnostics
            decisions.append({"seed": seed, "player": player.value,
                              "ply": len(session.state.history), **asdict(diag)})
            nodes += diag.nodes
            samples += diag.samples
            budget_limits += int(diag.budget_exhausted)
        proposal = session.propose(move, source='virtual-bot')
        session.commit(proposal.id)
        validate_state(session.state)
    state = session.state
    metrics = GameMetrics(seed, first_player.value, assisted, opponent,
                          state.winner.value if state.winner else None, state.reason,
                          len(session.events), sum(e.move.is_pass for e in session.events),
                          sum(t.points for t in state.hand(Player.ASSISTED)),
                          sum(t.points for t in state.hand(Player.OPPONENT)), 0,
                          (time.perf_counter() - started) * 1000, nodes, samples,
                          len(decisions), budget_limits)
    return GameRun(session, metrics, decisions)
