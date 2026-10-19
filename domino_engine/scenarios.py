"""Declarative scenario assertions; a failed expectation exits nonzero in the CLI."""
import json
from pathlib import Path
from .events import EventSession, ObservedScene, ObservedTile
from .knowledge import knowledge_for
from .rules import legal_moves
from .state import GameState, Player, from_hands
from .tiles import Move, OrientedTile, Tile


def load_initial(data):
    if 'version' in data:
        return GameState.from_dict(data)
    return from_hands(*(tuple(Tile(*t) for t in hand) for hand in data['hands']),
                      chain=tuple(OrientedTile(*t) for t in data.get('chain', [])),
                      turn=Player(data.get('turn', 'ASSISTED')), passes=data.get('passes', 0))


def assert_expected(session, expected):
    s = session.state
    actual = {"chain": [t.to_list() for t in s.chain],
              "ends": list(s.ends) if s.ends else None, "turn": s.turn.value,
              "terminal": s.terminal, "winner": s.winner.value if s.winner else None,
              "reason": s.reason, "passes": s.passes,
              "hand_counts": [len(h) for h in s.hands],
              "events": len(session.events), "legal_count": len(legal_moves(s)),
              "pending_legal": session.pending.legal if session.pending else None,
              "forbidden_opponent_values": sorted(knowledge_for(s, Player.ASSISTED).forbidden_opponent_values)}
    for key, value in expected.items():
        if key not in actual or actual[key] != value:
            raise AssertionError(f"{key}: expected {value!r}, got {actual.get(key)!r}")


def run_scenario(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    session = EventSession(load_initial(data['initial']))
    assert_expected(session, data.get('expect_initial', {}))
    for step in data.get('steps', []):
        action = step['action']
        if action in ('propose', 'correct'):
            move = Move.from_dict(step['move'])
            if action == 'propose':
                session.propose(move)
            else:
                session.correct(session.pending.id, move)
        elif action in ('observe', 'reread'):
            scene = ObservedScene(tuple(ObservedTile(t[0], t[1]) for t in step['tiles']),
                                  step.get('ambiguous', False))
            if action == 'observe': session.observe(scene)
            else: session.reread(session.pending.id, scene)
        elif action == 'commit':
            session.commit(session.pending.id)
        elif action == 'discard':
            session.discard(session.pending.id)
        elif action == 'undo':
            session.undo()
        elif action == 'replay':
            session = EventSession.from_json(session.to_json())
        else:
            raise ValueError(f'Unknown scenario action {action}')
        assert_expected(session, step.get('expect', {}))
    return {"scenario": data.get('name', str(path)), "steps": len(data.get('steps', [])), "passed": True}
