import random
import unittest
from dataclasses import replace
from domino_engine import *


class RulesTests(unittest.TestCase):
    def test_tiles_and_validation(self):
        self.assertEqual(len(set(ALL_TILES)), 28)
        self.assertEqual(Tile(6, 3), Tile(3, 6))
        for a, b in ((-1, 2), (0, 7), (True, 2), (1.0, 2)):
            with self.assertRaises(ValueError): Tile(a, b)
        with self.assertRaises(ValueError): Move(Tile(1, 2), Side.LEFT, OrientedTile(2, 3))

    def test_reproducible_deal_and_no_draw(self):
        s = deal(50)
        self.assertEqual(s, deal(50))
        self.assertEqual(tuple(map(len, s.hands)), (7, 7))
        self.assertEqual(len(s.excluded), 14)
        self.assertEqual(GameState.from_json(s.to_json()), s)
        self.assertTrue(all(not m.is_pass for m in legal_moves(s)))

    def test_opening_and_both_orientations(self):
        s = from_hands([Tile(1, 2), Tile(3, 3)], [Tile(6, 6)])
        moves = legal_moves(s)
        self.assertEqual(len(moves), 3)
        self.assertEqual({m.orientation for m in moves if m.tile == Tile(1, 2)},
                         {OrientedTile(1, 2), OrientedTile(2, 1)})
        self.assertTrue(all(m.side == Side.RIGHT for m in moves))

    def test_sides_flip_equal_ends_and_double(self):
        s = from_hands([Tile(1, 6), Tile(1, 1)], [Tile(4, 5)], chain=[OrientedTile(1, 2), OrientedTile(2, 3), OrientedTile(3, 1)])
        moves = legal_moves(s)
        self.assertEqual(len(moves), 4)
        left = Move(Tile(1, 6), Side.LEFT, OrientedTile(6, 1))
        right = Move(Tile(1, 6), Side.RIGHT, OrientedTile(1, 6))
        self.assertEqual(apply_move(s, left).ends, (6, 1))
        self.assertEqual(apply_move(s, right).ends, (1, 6))
        double = Move(Tile(1, 1), Side.LEFT, OrientedTile(1, 1))
        self.assertEqual(len(apply_move(s, double).chain), 4)
        with self.assertRaises(IllegalMove):
            apply_move(s, Move(Tile(1, 6), Side.LEFT, OrientedTile(1, 6)))

    def test_turn_identity_and_illegal_pass(self):
        s = deal(1)
        with self.assertRaises(IllegalMove): apply_move(s, legal_moves(s)[0], player=s.turn.other)
        self.assertEqual(legal_moves(s, s.turn.other), ())
        with self.assertRaises(IllegalMove): apply_move(s, Move())
        missing = next(t for t in ALL_TILES if t not in s.hand(s.turn))
        with self.assertRaises(IllegalMove):
            apply_move(s, Move(missing, Side.RIGHT, OrientedTile(missing.a, missing.b)))

    def test_forced_pass_block_draw_and_win(self):
        s = from_hands([Tile(1, 1)], [Tile(2, 2)], chain=[OrientedTile(6, 6)])
        self.assertEqual(legal_moves(s), (Move(),))
        a = apply_move(s, Move())
        self.assertEqual(a.excluded, s.excluded)
        self.assertEqual(a.hands, s.hands)
        self.assertFalse(a.terminal)
        b = apply_move(a, Move())
        self.assertTrue(b.terminal)
        self.assertEqual(b.reason, 'blocked')
        self.assertEqual(b.winner, Player.ASSISTED)
        self.assertEqual(legal_moves(b), ())
        with self.assertRaises(IllegalMove): apply_move(b, Move())
        draw = from_hands([Tile(0, 4)], [Tile(1, 3)], chain=[OrientedTile(6, 6)])
        self.assertIsNone(apply_move(apply_move(draw, Move()), Move()).winner)

    def test_immediate_empty_win_and_pass_reset(self):
        s = from_hands([Tile(1, 6)], [Tile(2, 2)], chain=[OrientedTile(6, 6)])
        s = apply_move(s, legal_moves(s)[0])
        self.assertTrue(s.terminal)
        self.assertEqual(s.reason, 'empty_hand')
        self.assertEqual(s.winner, Player.ASSISTED)
        s = from_hands([Tile(1, 1)], [Tile(2, 6), Tile(3, 3)], chain=[OrientedTile(6, 6)])
        s = apply_move(s, Move())
        s = apply_move(s, legal_moves(s)[0])
        self.assertEqual(s.passes, 0)

    def test_duplicates_broken_chain_and_bad_terminal_rejected(self):
        with self.assertRaises(ValueError): from_hands([Tile(1, 2)], [Tile(2, 1)])
        with self.assertRaises(ValueError):
            from_hands([Tile(0, 0)], [Tile(1, 1)], chain=[OrientedTile(2, 3), OrientedTile(4, 5)])
        s = deal(0)
        with self.assertRaises(ValueError): validate_state(replace(s, terminal=True))
        data = s.to_dict()
        data['excluded'][0] = data['hands'][0][0]
        with self.assertRaises(ValueError): GameState.from_dict(data)

    def test_random_transition_properties(self):
        rng = random.Random(77)
        for seed in range(40):
            s = deal(seed)
            count = 0
            while not s.terminal:
                prior = s
                s = apply_move(s, rng.choice(legal_moves(s)))
                self.assertEqual(s.turn, prior.turn.other)
                self.assertEqual(len(s.history), len(prior.history) + 1)
                self.assertEqual(s.excluded, prior.excluded)
                self.assertEqual(sum(map(len, prior.hands)) - sum(map(len, s.hands)),
                                 0 if s.history[-1].move.is_pass else 1)
                self.assertLess(len(s.chain), 15)
                validate_state(s)
                count += 1
                self.assertLess(count, 45)

    def test_private_snapshot_rejects_forged_history(self):
        s = deal(42)
        s = apply_move(s, legal_moves(s)[0])
        data = s.to_dict()
        data['history'][0]['player'] = s.turn.value
        with self.assertRaises(ValueError): GameState.from_dict(data)
        data = s.to_dict()
        data['history'][0]['ends_before'] = [1, 2]
        with self.assertRaises(ValueError): GameState.from_dict(data)

    def test_no_draw_distribution_bounds(self):
        with self.assertRaises(ValueError):
            from_hands(ALL_TILES[:8], ALL_TILES[8:15])

    def test_empty_hand_cannot_follow_pass_and_collections_are_frozen(self):
        with self.assertRaises(ValueError):
            from_hands([], [Tile(1, 1)], chain=[OrientedTile(6, 6)], passes=2)
        s = deal(1)
        hands = [list(h) for h in s.hands]
        mutable = replace(s, hands=hands)
        hands[0].clear()
        self.assertEqual(mutable, s)
        from domino_engine.state import PublicEvent
        ends = [1, 2]
        event = PublicEvent(Player.ASSISTED, Move(), ends)
        ends[0] = 6
        self.assertEqual(event.ends_before, (1, 2))
