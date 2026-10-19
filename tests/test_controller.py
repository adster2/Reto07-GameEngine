import time
import unittest
from domino_engine import *
from domino_engine.controller import GameController
from domino_engine.events import EventSession
from domino_engine.gui import headless_smoke


class ControllerTests(unittest.TestCase):
    def test_full_gui_controller_match(self):
        for level in (1, 5):
            result = headless_smoke(seed=42, level=level)
            self.assertTrue(result['terminal'])
            self.assertGreater(result['events'], 0)

    def test_stale_async_result_is_not_applied(self):
        c = GameController(session=EventSession(deal(42, first=Player.ASSISTED)))
        try:
            self.assertTrue(c.request_decision())
            c.replace_session(EventSession(deal(43)))
            deadline = time.monotonic() + 5
            while c.busy and time.monotonic() < deadline:
                result = c.poll_decision()
                if result: break
                time.sleep(.001)
            self.assertEqual(result, 'stale')
            self.assertEqual(c.session.state, deal(43))
            self.assertIsNone(c.ranking)
        finally: c.close()

    def test_manual_hand_is_explicit_and_atomic(self):
        c = GameController()
        try:
            initial = c.session.state
            with self.assertRaises(ValueError): c.register_manual_hand([Tile(0, 0)] * 7)
            self.assertEqual(c.session.state, initial)
            hand = tuple(Tile(0, x) for x in range(7))
            c.register_manual_hand(hand)
            self.assertEqual(c.snapshot().hand, hand)
            self.assertEqual(c.snapshot().opponent_count, 7)
            self.assertFalse(hasattr(c.snapshot(), 'excluded'))
        finally: c.close()

    def test_cpu_uses_strategy_and_follows_difficulty(self):
        c = GameController(seed=42, level=4)
        try:
            self.assertEqual(c.opponent_name, 'ai4')
            self.assertEqual(c.session.state.turn, Player.OPPONENT)
            c.request_decision()
            deadline = time.monotonic() + 10
            while c.busy and time.monotonic() < deadline:
                c.poll_decision()
                time.sleep(.001)
            self.assertIsNotNone(c.session.pending)
            self.assertTrue(c.session.pending.legal)
            self.assertIsNotNone(c.last_cpu_diagnostics)
            self.assertEqual(c.last_cpu_diagnostics.requested_depth, 4)
            self.assertGreater(c.last_cpu_diagnostics.nodes, 0)
            self.assertEqual(c.cpu_decisions, 1)
            # Even an AI CPU must wait for human confirmation.
            self.assertEqual(len(c.session.events), 0)
            c.confirm()
            c.set_level(5)
            self.assertEqual(c.opponent_name, 'ai5')
        finally: c.close()
