import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
from domino_engine import Move, Player, Tile, deal, from_hands, legal_moves, validate_state
from domino_engine.events import EventSession, ProposalError
from domino_engine.knowledge import KnowledgeState, knowledge_for
from domino_engine.simulation import GreedyBot
from domino_engine.web_bridge import WebGame
from scripts.build_web import build, MODULES


class WebBridgeTests(unittest.TestCase):
    def request(self, game, command, **extra):
        return game.handle({'command': command, 'token': game.token, **extra})

    def test_snapshot_never_exposes_referee_secrets(self):
        game = WebGame(42, 5)
        response = game.snapshot()
        text = json.dumps(response)
        for key in ('"hands"', '"excluded"', '"seed"'):
            self.assertNotIn(key, text)
        self.assertEqual(response['view']['hand'], [t.to_list() for t in game.session.state.hand(Player.ASSISTED)])
        self.assertIsNone(response['result'])
        response = self.request(game, 'cpu')
        self.assertTrue(response['pending']['legal'])
        self.assertEqual(response['cpu_diagnostics']['completed_depth'], 5)
        self.assertEqual(response['ranking'], [])  # Never send the CPU's ranking/hand.
        self.assertEqual(response['event_count'], 0)

    def test_cpu_receives_only_knowledge(self):
        game = WebGame(42, 3)
        def choose(bot, view):
            self.assertIsInstance(view, KnowledgeState)
            self.assertEqual(view.observer, Player.OPPONENT)
            from domino_engine.strategy import StrategyEngine
            bot.last_ranking = StrategyEngine(bot.config).rank(view)
            return bot.last_ranking.recommendation
        with patch('domino_engine.simulation.StrategyBot.choose', choose):
            self.request(game, 'cpu')

    def test_complete_games_all_five_levels_and_replay(self):
        for level in range(1, 6):
            for seed in (41, 42, 73):
                with self.subTest(level=level, seed=seed):
                    game = WebGame(seed, level)
                    while not game.session.state.terminal:
                        if game.session.state.turn == Player.OPPONENT:
                            self.request(game, 'cpu')
                        else:
                            move = GreedyBot().choose(knowledge_for(game.session.state, Player.ASSISTED))
                            self.request(game, 'propose', move=move.to_dict())
                        pending = game.session.pending
                        self.assertTrue(pending.legal)
                        self.request(game, 'confirm', proposal_id=pending.id)
                        validate_state(game.session.state)
                        self.assertLess(len(game.session.events), 45)
                    self.assertIsNotNone(game.snapshot()['result'])
                    saved = self.request(game, 'save')
                    restored = WebGame(10)
                    self.request(restored, 'load', **saved)
                    self.assertEqual(restored.session.state, game.session.state)
                    self.assertEqual(restored.level, level)

    def test_duplicate_confirm_and_stale_new_game_ids(self):
        game = WebGame(43)
        self.request(game, 'propose', move=legal_moves(game.session.state)[0].to_dict())
        commit = {'command': 'confirm', 'token': game.token, 'proposal_id': game.session.pending.id}
        a = game.handle(commit)
        self.assertEqual(game.handle(commit), a)
        self.assertEqual(len(game.session.events), 1)
        self.request(game, 'new_game', seed=43)
        self.request(game, 'propose', move=legal_moves(game.session.state)[0].to_dict())
        with self.assertRaises(ProposalError): game.handle(commit)
        self.assertEqual(len(game.session.events), 0)

    def test_illegal_pending_correction_reread_and_undo(self):
        game = WebGame(43)
        initial = game.session.state
        self.request(game, 'propose', move=Move().to_dict())
        self.assertFalse(game.snapshot()['pending']['legal'])
        with self.assertRaises(ValueError): self.request(game, 'confirm', proposal_id=game.session.pending.id)
        move = legal_moves(initial)[0]
        self.request(game, 'correct', move=move.to_dict())
        self.request(game, 'reread', move=move.to_dict())
        self.assertTrue(game.session.pending.legal)
        self.assertEqual(game.session.state, initial)
        with self.assertRaises(ProposalError): self.request(game, 'propose', move=move.to_dict())
        self.request(game, 'confirm', proposal_id=game.session.pending.id)
        self.request(game, 'undo')
        self.assertEqual(game.session.state, initial)

    def test_turn_level_and_load_validation_are_atomic(self):
        game = WebGame(42)
        initial = game.snapshot()
        with self.assertRaises(ProposalError): self.request(game, 'propose', move=Move().to_dict())
        for level in (0, 6, True, '5'):
            with self.assertRaises(ValueError): self.request(game, 'new_game', level=level)
            self.assertEqual(game.snapshot(), initial)
        with self.assertRaises(ValueError): self.request(game, 'load', save='{}')
        self.assertEqual(game.snapshot(), initial)
        old_token = game.token
        self.request(game, 'set_level', level=5)
        with self.assertRaises(ProposalError): game.handle({'command': 'cpu', 'token': old_token})
        self.assertEqual(game.level, 5)

    def test_advice_all_legal_moves_and_json_protocol(self):
        game = WebGame(43, 4)
        reply = json.loads(game.handle_json(json.dumps({'command':'rank', 'token':game.token})))
        self.assertEqual({json.dumps(r['move'], sort_keys=True) for r in reply['ranking']},
                         {json.dumps(m.to_dict(), sort_keys=True) for m in legal_moves(game.session.state)})
        self.assertEqual(reply['advice_diagnostics']['completed_depth'], 4)
        self.assertEqual(len(game.session.events), 0)

    def test_static_build_reuses_byte_identical_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = build(tmp)
            self.assertEqual(len(manifest['files']), len(MODULES))
            for entry in manifest['files']:
                self.assertEqual(Path(entry['path']).read_bytes(), (Path(tmp)/'engine'/entry['path']).read_bytes())
                self.assertEqual(hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest(), entry['sha256'])
            html = (Path(tmp)/'index.html').read_text()
            self.assertIn(manifest['source_commit'], html)
            self.assertTrue((Path(tmp)/'.nojekyll').is_file())
        with self.assertRaises(ValueError): build('.')
        with self.assertRaises(ValueError): build('domino_engine')
