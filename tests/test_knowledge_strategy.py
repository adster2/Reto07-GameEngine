import random
import unittest
from dataclasses import FrozenInstanceError, replace
from domino_engine import *
from domino_engine.state import PublicEvent
from domino_engine.knowledge import *
from domino_engine.strategy import *


class KnowledgeStrategyTests(unittest.TestCase):
    def test_information_boundary_and_immutability(self):
        s = deal(55)
        v = knowledge_for(s, s.turn)
        self.assertFalse(hasattr(v, 'hands'))
        self.assertFalse(hasattr(v, 'excluded'))
        self.assertFalse(hasattr(v, 'seed'))
        self.assertEqual(len(v.unseen), 21)
        with self.assertRaises(FrozenInstanceError): v.opponent_count = 5
        with self.assertRaises(TypeError): StrategyEngine().rank(s)

    def test_anticheat_ranking_all_levels(self):
        a = deal(73)
        me = a.turn
        unseen = [t for t in ALL_TILES if t not in a.hand(me)]
        rng = random.Random(719)
        rng.shuffle(unseen)
        hands = (a.hand(me), tuple(unseen[:7])) if me == Player.ASSISTED else (tuple(unseen[:7]), a.hand(me))
        b = from_hands(*hands, turn=me, seed=99999)
        self.assertNotEqual(a.hand(me.other), b.hand(me.other))
        va, vb = knowledge_for(a, me), knowledge_for(b, me)
        self.assertEqual(va, vb)
        for level in range(1, 6):
            engine = StrategyEngine(SearchConfig(level, samples=3, max_nodes=100000, time_limit_ms=10000, seed=124))
            x, y = engine.rank(va), engine.rank(vb)
            self.assertEqual(x.moves, y.moves)
            self.assertEqual(x.recommendation, y.recommendation)
            self.assertEqual(x.diagnostics.nodes, y.diagnostics.nodes)

    def test_pass_constraints_and_unseen_includes_excluded(self):
        s = from_hands([Tile(0, 0), Tile(1, 1)], [Tile(2, 3), Tile(4, 5)],
                       chain=[OrientedTile(6, 6)], turn=Player.OPPONENT)
        s = apply_move(s, Move())
        view = knowledge_for(s, Player.ASSISTED)
        self.assertEqual(view.forbidden_opponent_values, frozenset({6}))
        self.assertGreater(len(view.unseen), view.opponent_count)
        for seed in range(30):
            sampled = sample_world(view, random.Random(seed))
            self.assertTrue(all(not t.contains(6) for t in sampled.hand(Player.OPPONENT)))
            self.assertEqual(len(sampled.excluded), len(s.excluded))
            validate_state(sampled)
        # Pass endpoints remain 6,6 after later changes, rather than today's endpoints.
        changed = replace(view, chain=(OrientedTile(6, 2),))
        self.assertEqual(changed.forbidden_opponent_values, frozenset({6}))
        self.assertTrue(any(t.contains(2) for t in changed.opponent_candidates))

    def test_five_depths_and_complete_rankings(self):
        s = deal(42)
        view = knowledge_for(s, s.turn)
        for level in range(1, 6):
            r = StrategyEngine(SearchConfig(level, samples=2, max_nodes=100000, time_limit_ms=10000)).rank(view)
            self.assertEqual(r.diagnostics.completed_depth, level)
            self.assertEqual(r.diagnostics.deepest_visited, level)
            self.assertFalse(r.diagnostics.budget_exhausted)
            self.assertEqual(set(x.move for x in r.moves), set(legal_moves(s)))
            self.assertEqual([x.score for x in r.moves], sorted((x.score for x in r.moves), reverse=True))

    def test_budget_fallback_and_determinism(self):
        view = knowledge_for(deal(1), deal(1).turn)
        engine = StrategyEngine(SearchConfig(5, samples=8, max_nodes=1, time_limit_ms=10000))
        a, b = engine.rank(view), engine.rank(view)
        self.assertEqual(a.moves, b.moves)
        self.assertEqual(a.diagnostics.limit, 'nodes')
        self.assertEqual(a.diagnostics.nodes, 1)
        self.assertEqual(a.diagnostics.completed_depth, 1)
        self.assertIn(a.recommendation, view.legal_moves())
        self.assertEqual(len(a.moves), len(view.legal_moves()))
        r = StrategyEngine(SearchConfig(5, time_limit_ms=0.0001)).rank(view)
        self.assertEqual(r.diagnostics.limit, 'time')

    def test_pass_counts_as_one_ply_and_terminal_scale(self):
        s = from_hands([Tile(0, 0)], [Tile(1, 1)], chain=[OrientedTile(6, 6)])
        view = knowledge_for(s, s.turn)
        r = StrategyEngine(SearchConfig(2, samples=3)).rank(view)
        self.assertTrue(r.recommendation.is_pass)
        self.assertEqual(r.diagnostics.deepest_visited, 2)
        s = from_hands([Tile(1, 6)], [Tile(4, 4)], chain=[OrientedTile(6, 6)])
        r = StrategyEngine(SearchConfig(5, samples=3)).rank(knowledge_for(s, s.turn))
        self.assertEqual(r.moves[0].score, 1000)
        s = apply_move(s, r.recommendation)
        self.assertEqual(StrategyEngine().rank(knowledge_for(s, s.turn)).moves, ())

    def test_seed_independent_of_deal_seed(self):
        s = deal(3)
        v = knowledge_for(s, s.turn)
        self.assertEqual(v, knowledge_for(replace(s, seed=292292), s.turn))
        with self.assertRaises(ValueError): SearchConfig(6)
        with self.assertRaises(ValueError): SearchConfig(max_nodes=-1)

    def test_inconsistent_knowledge_is_diagnosed(self):
        s = deal(42, first=Player.ASSISTED)
        v = knowledge_for(s, s.turn)
        events = tuple(PublicEvent(Player.OPPONENT, Move(), (n, n)) for n in range(7))
        v = replace(v, history=events)
        with self.assertRaises(InconsistentKnowledge): sample_world(v, random.Random(0))
        r = StrategyEngine(SearchConfig(5)).rank(v)
        self.assertEqual(r.diagnostics.limit, 'inconsistent_knowledge')
        self.assertIn(r.recommendation, v.legal_moves())
