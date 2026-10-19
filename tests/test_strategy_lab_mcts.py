import itertools
import random
import unittest
from unittest.mock import patch

from domino_engine.knowledge import KnowledgeState,knowledge_for
from domino_engine.rules import apply_move
from domino_engine.state import Player,deal,from_hands
from domino_engine.tiles import ALL_TILES,Move,OrientedTile,Side,Tile
from strategy_lab.arena import run_match
from strategy_lab.ismcts import MCTSConfig,ISMCTSEngine,rollout_move
from strategy_lab.tactics import block_value,score_moves


class TacticalTests(unittest.TestCase):
    def test_block_value_matches_complete_enumeration_including_zero_pips(self):
        candidates = (Tile(0,0),Tile(1,1),Tile(0,6),Tile(2,3))
        for own in (0,2,5,12):
            expected = 0
            hands = list(itertools.combinations(candidates,2))
            for hand in hands:
                if any(t.contains(6) for t in hand): continue
                points = sum(t.points for t in hand)
                expected += 1 if points>own else -1 if points<own else 0
            self.assertAlmostEqual(block_value(candidates,2,(6,6),own),expected/len(hands))

    def test_blocking_is_good_or_bad_depending_on_residual_points(self):
        candidates = (Tile(1,1),Tile(2,2),Tile(3,3))
        self.assertEqual(block_value(candidates,1,(6,6),0),1)
        self.assertEqual(block_value(candidates,1,(6,6),12),-1)

    def test_public_pass_makes_double_pressure_meaningful(self):
        state = from_hands([Tile(6,6),Tile(3,6),Tile(0,0)],[Tile(2,4)],
            chain=[OrientedTile(6,0),OrientedTile(0,1),OrientedTile(1,6)],turn=Player.OPPONENT)
        state = apply_move(state,Move())
        view = knowledge_for(state,Player.ASSISTED)
        scores,notes = score_moves(view)
        double = next(m for m in scores if m.tile==Tile(6,6))
        other = next(m for m in scores if m.tile==Tile(3,6))
        self.assertIn('P(passo avversario)=1.000',notes[double])
        self.assertGreater(scores[double],scores[other])

    def test_bridge_removal_penalizes_stranding_other_tiles(self):
        state = from_hands([Tile(1,2),Tile(1,3),Tile(2,4)],[Tile(5,6)],chain=[OrientedTile(0,1)])
        scores,notes = score_moves(knowledge_for(state,state.turn))
        bridge = next(m for m in scores if m.tile==Tile(1,3))
        alternative = next(m for m in scores if m.tile==Tile(1,2))
        self.assertIn('ponti persi 2',notes[bridge])
        self.assertIn('ponti persi 1',notes[alternative])
        self.assertGreater(scores[alternative],scores[bridge])


class ISMCTSTests(unittest.TestCase):
    def test_shared_root_visits_account_only_for_completed_simulations(self):
        state = deal(42)
        view = knowledge_for(state,state.turn)
        cfg = MCTSConfig(iterations=32,samples=16,max_nodes=100000,time_limit_ms=10000)
        ranking = ISMCTSEngine(cfg).rank(view)
        self.assertEqual(ranking.diagnostics.iterations_completed,32)
        self.assertEqual(sum(n for _,n in ranking.diagnostics.root_visits),32)
        self.assertEqual({r.move for r in ranking.moves},set(view.legal_moves()))
        self.assertTrue(all(n for _,n in ranking.diagnostics.root_visits))
        self.assertEqual(ranking.moves[0].score,max(n for _,n in ranking.diagnostics.root_visits))
        self.assertLessEqual(ranking.diagnostics.deepest_visited,44)

    def test_root_coverage_fallback_never_exposes_a_partial_ranking(self):
        state = deal(42)
        view = knowledge_for(state,state.turn)
        prior,_ = score_moves(view)
        for cfg in (MCTSConfig(iterations=1),MCTSConfig(max_nodes=0),MCTSConfig(time_limit_ms=.000001)):
            result = ISMCTSEngine(cfg).rank(view)
            self.assertEqual(result.diagnostics.completed_depth,0)
            self.assertEqual({r.move:r.score for r in result.moves},prior)

    def test_anticheat_and_repeatability_across_tree_depths(self):
        a = deal(73)
        observer = a.turn
        unseen = [t for t in ALL_TILES if t not in a.hand(observer)]
        random.Random(719).shuffle(unseen)
        hands = (a.hand(observer),unseen[:7]) if observer==Player.ASSISTED else (unseen[:7],a.hand(observer))
        b = from_hands(*hands,turn=observer,seed=999)
        va,vb = knowledge_for(a,observer),knowledge_for(b,observer)
        self.assertEqual(va,vb)
        for level in (1,3,5):
            cfg = MCTSConfig(level=level,iterations=16,samples=8,time_limit_ms=10000,max_nodes=100000)
            x,y = ISMCTSEngine(cfg).rank(va),ISMCTSEngine(cfg).rank(vb)
            self.assertEqual(x.moves,y.moves)
            self.assertEqual(x.diagnostics.root_visits,y.diagnostics.root_visits)
            self.assertEqual(x.diagnostics.nodes,y.diagnostics.nodes)
        with self.assertRaises(TypeError): ISMCTSEngine().rank(a)

    def test_rollout_decisions_receive_only_actor_knowledge(self):
        state = deal(42)
        received = []
        def inspect(view,rng):
            self.assertIsInstance(view,KnowledgeState)
            self.assertFalse(hasattr(view,'hands'))
            self.assertFalse(hasattr(view,'excluded'))
            received.append(view.observer)
            return rollout_move(view,rng)
        with patch('strategy_lab.ismcts.rollout_move',side_effect=inspect):
            ISMCTSEngine(MCTSConfig(iterations=8,samples=4,time_limit_ms=10000)).rank(knowledge_for(state,state.turn))
        self.assertEqual(set(received),set(Player))

    def test_actual_game_replays_through_the_accepted_referee(self):
        row,decisions,journal = run_match(71001,config=MCTSConfig(iterations=16,samples=8,time_limit_ms=10000))
        self.assertEqual(row['rule_violations'],0)
        self.assertTrue(row['replay_verified'])
        self.assertEqual(row['algorithm'],'ismcts')
        self.assertTrue(decisions)


if __name__ == '__main__': unittest.main()
