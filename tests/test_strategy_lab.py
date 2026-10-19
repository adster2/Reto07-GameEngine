import itertools
import math
import random
import unittest

from domino_engine.knowledge import knowledge_for,InconsistentKnowledge
from domino_engine.rules import apply_move,legal_moves
from domino_engine.state import Player,deal,from_hands,PublicEvent
from domino_engine.tiles import ALL_TILES,Move,OrientedTile,Side,Tile
from strategy_lab.belief import BeliefState
from strategy_lab.heuristic import state_value
from strategy_lab.minimax import LabConfig,MinimaxEngine


class BeliefTests(unittest.TestCase):
    def test_starting_probabilities_account_for_fourteen_excluded(self):
        state = deal(42)
        belief = BeliefState(knowledge_for(state,state.turn))
        self.assertEqual(len(belief.unseen),21)
        self.assertEqual(belief.hand_count,math.comb(21,7))
        tiles = belief.tiles()
        self.assertAlmostEqual(sum(t.opponent_probability for t in tiles),7)
        self.assertAlmostEqual(sum(t.excluded_probability for t in tiles),14)
        for t in tiles:
            self.assertAlmostEqual(t.opponent_probability,0 if t.tile in state.hand(state.turn) else 1/3)

    def test_own_play_does_not_remove_another_unknown_and_opponent_play_does(self):
        state = from_hands([Tile(0,1),Tile(2,3)],[Tile(1,4),Tile(5,5)],chain=[OrientedTile(0,0)])
        a = BeliefState(knowledge_for(state,Player.ASSISTED))
        state = apply_move(state,Move(Tile(0,1),Side.RIGHT,OrientedTile(0,1)))
        b = BeliefState(knowledge_for(state,Player.ASSISTED))
        self.assertEqual(a.unseen,b.unseen)
        state = apply_move(state,Move(Tile(1,4),Side.RIGHT,OrientedTile(1,4)))
        c = BeliefState(knowledge_for(state,Player.ASSISTED))
        self.assertEqual(set(c.unseen),set(b.unseen)-{Tile(1,4)})
        self.assertEqual(c.view.opponent_count,1)
        self.assertEqual(next(t.opponent_probability for t in c.tiles() if t.tile==Tile(1,4)),0)

    def test_pass_is_hard_evidence_using_historical_ends(self):
        state = from_hands([Tile(0,6),Tile(1,2)],[Tile(2,3),Tile(4,5)],
                           chain=[OrientedTile(6,6)],turn=Player.OPPONENT)
        state = apply_move(state,Move())
        b = BeliefState(knowledge_for(state,Player.ASSISTED))
        self.assertTrue(b.certainly_excluded)
        self.assertTrue(all(not t.contains(6) for t in b.candidates))
        state = apply_move(state,Move(Tile(0,6),Side.LEFT,OrientedTile(0,6)))
        b = BeliefState(knowledge_for(state,Player.ASSISTED))
        self.assertEqual(b.view.forbidden_opponent_values,frozenset({6}))
        self.assertTrue(any(t.contains(0) for t in b.candidates))

    def test_sampling_matches_uniform_combination_ranks_without_duplicates(self):
        state = deal(11)
        belief = BeliefState(knowledge_for(state,state.turn))
        ranks = set(random.Random(123).sample(range(belief.hand_count),32))
        expected = {hand for index,hand in enumerate(itertools.combinations(belief.candidates,7)) if index in ranks}
        actual = belief.hands(32,random.Random(123))
        self.assertEqual(len(actual),len(set(actual)))
        self.assertEqual(set(actual),expected)

    def test_small_belief_is_enumerated_and_pass_probability_is_exact(self):
        state = from_hands([Tile(0,1),Tile(1,1)],[Tile(2,3)],chain=[OrientedTile(6,6)])
        belief = BeliefState(knowledge_for(state,Player.ASSISTED))
        hands = belief.hands(64,random.Random(1))
        self.assertEqual(len(hands),belief.hand_count)
        expected = sum(not any(t.contains(0) or t.contains(6) for t in h) for h in hands)/len(hands)
        self.assertAlmostEqual(belief.pass_probability((0,6)),expected)
        for world in belief.worlds(64,random.Random(1)):
            self.assertEqual(knowledge_for(world,Player.ASSISTED),belief.view)

    def test_invalid_knowledge_is_not_silently_repaired(self):
        state = deal(42)
        from dataclasses import replace
        view = knowledge_for(state,state.turn)
        events = tuple(PublicEvent(view.observer.other,Move(),(n,n)) for n in range(7))
        with self.assertRaises(InconsistentKnowledge): BeliefState(replace(view,history=events))
        with self.assertRaises(TypeError): BeliefState(state)

    def test_finished_opponent_has_no_unknown_tiles_left_in_hand(self):
        state = from_hands([Tile(1,1)],[],chain=[OrientedTile(6,6)])
        belief = BeliefState(knowledge_for(state,Player.ASSISTED))
        self.assertEqual(belief.candidates,())
        self.assertEqual(belief.hand_count,1)
        self.assertEqual(set(belief.certainly_excluded),set(belief.unseen))
        self.assertTrue(all(t.opponent_probability == 0 for t in belief.tiles()))


class MinimaxTests(unittest.TestCase):
    def test_alpha_beta_matches_unpruned_minimax_on_same_hypotheses(self):
        state = from_hands([Tile(1,6),Tile(1,2)],[Tile(2,6),Tile(0,4)],chain=[OrientedTile(6,6)])
        view = knowledge_for(state,state.turn)
        cfg = LabConfig(level=4,samples=5,max_nodes=100000,time_limit_ms=10000,seed=17)
        result = MinimaxEngine(cfg).rank(view)
        worlds = BeliefState(view).worlds(cfg.samples,random.Random(cfg.seed))
        def reference(s,depth):
            if not depth or s.terminal: return state_value(s,view.observer,cfg.weights)
            values = [reference(apply_move(s,m),depth-1) for m in legal_moves(s)]
            return max(values) if s.turn==view.observer else min(values)
        for row in result.moves:
            expected = sum(reference(apply_move(s,row.move),cfg.level-1) for s in worlds)/len(worlds)
            self.assertAlmostEqual(row.score,expected)
        self.assertEqual(result.diagnostics.completed_depth,4)

    def test_changed_real_secrets_do_not_change_belief_or_any_level_ranking(self):
        a = deal(73)
        observer = a.turn
        unseen = [t for t in ALL_TILES if t not in a.hand(observer)]
        random.Random(719).shuffle(unseen)
        hands = (a.hand(observer),unseen[:7]) if observer==Player.ASSISTED else (unseen[:7],a.hand(observer))
        b = from_hands(*hands,turn=observer,seed=9999)
        self.assertNotEqual(a.hand(observer.other),b.hand(observer.other))
        va,vb = knowledge_for(a,observer),knowledge_for(b,observer)
        self.assertEqual(va,vb)
        for depth in range(1,6):
            cfg = LabConfig(level=depth,samples=4,max_nodes=100000,time_limit_ms=10000,seed=23)
            x,y = MinimaxEngine(cfg).rank(va),MinimaxEngine(cfg).rank(vb)
            self.assertEqual(x.moves,y.moves)
            self.assertEqual(x.belief.to_dict(),y.belief.to_dict())
            self.assertEqual(x.diagnostics.nodes,y.diagnostics.nodes)
            self.assertEqual(x.diagnostics.completed_depth,depth)
            self.assertLessEqual(x.diagnostics.deepest_visited,depth)
        with self.assertRaises(TypeError): MinimaxEngine().rank(a)

    def test_budget_fallback_is_complete_and_never_uses_partial_iteration(self):
        state = deal(42)
        view = knowledge_for(state,state.turn)
        zero = MinimaxEngine(LabConfig(max_nodes=0)).rank(view)
        interrupted = MinimaxEngine(LabConfig(max_nodes=5)).rank(view)
        self.assertEqual(zero.moves,interrupted.moves)
        self.assertEqual(zero.diagnostics.completed_depth,0)
        self.assertEqual(interrupted.diagnostics.limit,'nodes')
        self.assertEqual(interrupted.diagnostics.nodes,5)
        self.assertEqual({r.move for r in zero.moves},set(view.legal_moves()))
        timed = MinimaxEngine(LabConfig(time_limit_ms=.000001)).rank(view)
        self.assertEqual(timed.diagnostics.limit,'time')

    def test_passes_count_as_plies_and_block_outcomes_are_not_pip_shedding(self):
        state = from_hands([Tile(0,0)],[Tile(1,1)],chain=[OrientedTile(6,6)])
        result = MinimaxEngine(LabConfig(level=5,samples=32)).rank(knowledge_for(state,state.turn))
        self.assertTrue(result.recommendation.is_pass)
        self.assertEqual(result.diagnostics.completed_depth,5)
        self.assertEqual(result.diagnostics.deepest_visited,2)
        self.assertEqual(state_value(state,Player.ASSISTED),1000)
        self.assertEqual(state_value(state,Player.OPPONENT),-1000)

    def test_immediate_win_and_terminal_ranking(self):
        state = from_hands([Tile(1,6)],[Tile(4,4)],chain=[OrientedTile(6,6)])
        result = MinimaxEngine(LabConfig(level=3)).rank(knowledge_for(state,state.turn))
        self.assertEqual(result.moves[0].score,1000)
        terminal = apply_move(state,result.recommendation)
        self.assertEqual(MinimaxEngine().rank(knowledge_for(terminal,Player.ASSISTED)).moves,())

    def test_deterministic_ranking_and_configuration_validation(self):
        state = deal(3)
        view = knowledge_for(state,state.turn)
        engine = MinimaxEngine(LabConfig(seed=23,time_limit_ms=10000))
        a,b = engine.rank(view),engine.rank(view)
        self.assertEqual(a.moves,b.moves)
        self.assertEqual(a.diagnostics.nodes,b.diagnostics.nodes)
        for kwargs in ({'level':6},{'samples':0},{'max_nodes':-1},{'time_limit_ms':math.inf},{'risk':2}):
            with self.assertRaises(ValueError): LabConfig(**kwargs)


if __name__ == '__main__': unittest.main()
