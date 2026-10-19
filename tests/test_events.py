import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from domino_engine import *
from domino_engine.events import *


class EventTests(unittest.TestCase):
    def setUp(self):
        self.initial = from_hands([Tile(3, 6), Tile(1, 1)], [Tile(0, 2), Tile(4, 4)])
        self.session = EventSession(self.initial)

    def test_misread_correct_confirm_duplicate_undo(self):
        p = self.session.observe(ObservedScene((ObservedTile(3, 5),)))
        self.assertFalse(p.legal)
        self.assertEqual(self.session.state, self.initial)
        with self.assertRaises(IllegalMove): self.session.commit(p.id)
        p = self.session.correct(p.id, Move(Tile(3, 6), Side.RIGHT, OrientedTile(3, 6)))
        self.assertTrue(p.legal)
        s = self.session.commit(p.id)
        self.assertEqual(s.hands[0], (Tile(1, 1),))
        self.assertEqual(self.session.commit(p.id), s)
        self.assertEqual(len(self.session.events), 1)
        restored = EventSession.from_json(self.session.to_json())
        self.assertEqual(restored.state, s)
        self.assertEqual(self.session.undo(), self.initial)
        with self.assertRaises(ProposalError): self.session.commit(p.id)

    def test_wrong_side_reread_and_discard(self):
        s = from_hands([Tile(1, 6), Tile(2, 2)], [Tile(0, 0)], chain=[OrientedTile(3, 6)])
        session = EventSession(s)
        p = session.propose(Move(Tile(1, 6), Side.LEFT, OrientedTile(1, 6)))
        self.assertFalse(p.legal)
        p = session.reread(p.id, ObservedScene((ObservedTile(3, 6),
                            ObservedTile(6, 1, Side.RIGHT))))
        self.assertTrue(p.legal)
        self.assertEqual(p.new_ends, (3, 1))
        session.discard(p.id)
        self.assertEqual(session.state, s)

    def test_pending_exclusion_and_illegal_real_move(self):
        p = self.session.propose(Move())
        with self.assertRaises(ProposalError): self.session.propose(legal_moves(self.initial)[0])
        with self.assertRaises(ProposalError): self.session.undo()
        with self.assertRaises(IllegalMove): self.session.commit(p.id)
        self.assertEqual(self.session.state, self.initial)

    def test_zero_multiple_ambiguous_and_low_confidence(self):
        for scene in (ObservedScene(()), ObservedScene((ObservedTile(1, 1), ObservedTile(3, 6))),
                      ObservedScene((ObservedTile(3, 6),), True),
                      ObservedScene((ObservedTile(3, 6, confidence=.4),))):
            self.assertIsNone(self.session.observe(scene))
            self.assertIsNone(self.session.pending)
            self.assertEqual(self.session.state, self.initial)
        p = self.session.observe(ObservedScene((ObservedTile(3, 6),)))
        self.assertIsNone(self.session.reread(p.id, ObservedScene(())))
        with self.assertRaises(IllegalMove): self.session.commit(p.id)

    def test_baseline_is_confirmed_and_movements_are_ignored(self):
        p = self.session.propose(legal_moves(self.initial)[0])
        self.session.commit(p.id)
        self.assertIsNone(self.session.observe(ObservedScene(())))
        self.assertIsNone(self.session.observe(ObservedScene((ObservedTile(1, 1),))))
        baseline = tuple(ObservedTile(t.left, t.right) for t in self.session.state.chain)
        self.assertIsNone(self.session.observe(ObservedScene(baseline)))

    def test_concurrent_double_commit(self):
        p = self.session.propose(legal_moves(self.initial)[0])
        with ThreadPoolExecutor(4) as pool:
            states = list(pool.map(lambda _: self.session.commit(p.id), range(8)))
        self.assertTrue(all(s == states[0] for s in states))
        self.assertEqual(len(self.session.events), 1)

    def test_replay_tampering_rejected(self):
        p = self.session.propose(legal_moves(self.initial)[0])
        self.session.commit(p.id)
        data = self.session.to_dict()
        data['events'][0]['player'] = Player.OPPONENT.value
        with self.assertRaises(IllegalMove): EventSession.from_json(json.dumps(data))

    def test_complete_game_undo_all_and_replay(self):
        session = EventSession(deal(17))
        initial = session.state
        while not session.state.terminal:
            p = session.propose(legal_moves(session.state)[0])
            session.commit(p.id)
        saved = EventSession.from_json(session.to_json())
        self.assertEqual(saved.state, session.state)
        for _ in range(len(session.events)):
            session.undo()
        self.assertEqual(session.state, initial)

    def test_loaded_event_ids_are_never_reused(self):
        p = self.session.propose(legal_moves(self.initial)[0])
        self.session.commit(p.id)
        data = self.session.to_dict()
        data['events'][0]['id'] = 'move-3'
        data['serial'] = 0
        loaded = EventSession.from_json(json.dumps(data))
        for _ in range(2):
            if loaded.state.terminal: break
            p = loaded.propose(legal_moves(loaded.state)[0])
            self.assertNotEqual(p.id, 'move-3')
            loaded.commit(p.id)
        ids = [e.id for e in loaded.events]
        self.assertEqual(len(ids), len(set(ids)))
