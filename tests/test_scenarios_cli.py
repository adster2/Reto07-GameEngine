import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from domino_engine.cli import main
from domino_engine.scenarios import run_scenario
from domino_engine.simulation import play_game
from domino_engine.experiments import audit_transcripts, tournament, benchmark, stress
from domino_engine.strategy import SearchConfig


class ScenarioAndCLITests(unittest.TestCase):
    def test_all_json_scenarios(self):
        files = sorted(Path('scenarios').glob('*.json'))
        self.assertEqual(len(files), 8)
        for file in files:
            with self.subTest(file=file): self.assertTrue(run_scenario(file)['passed'])

    def test_cli_full_match_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            path = str(Path(tmp)/'game.json')
            self.assertEqual(main(['play','--seed','42','--save',path,'--verbose']), 0)
            self.assertEqual(main(['replay',path]), 0)
            self.assertEqual(main(['scenario','scenarios/01.json']), 0)

    def test_reproducibility_except_clock(self):
        a, b = play_game(144, 'ai5', 'random'), play_game(144, 'ai5', 'random')
        self.assertEqual(a.session.state, b.session.state)
        self.assertEqual(a.session.events, b.session.events)
        ma, mb = a.metrics.to_dict(), b.metrics.to_dict()
        ma.pop('elapsed_ms'); mb.pop('elapsed_ms')
        self.assertEqual(ma, mb)

    def test_measurement_runners_and_balanced_seats(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = tournament(tmp, seeds=2, levels=(1,), opponents=('random',), config=SearchConfig(samples=2))
            self.assertEqual(report['groups'][0]['games'], 8)
            self.assertEqual(report['groups'][0]['rule_violations'], 0)
            self.assertEqual(audit_transcripts(Path(tmp)/'TOURNAMENT_EVENTS.jsonl.gz')['games'], 8)
            bench = benchmark(Path(tmp)/'bench.csv', positions=3, config=SearchConfig(5,samples=2))
            self.assertTrue(bench['latency_gate_pass'])
            self.assertEqual(stress(Path(tmp)/'stress.csv',games=10)['replays_verified'], 10)
