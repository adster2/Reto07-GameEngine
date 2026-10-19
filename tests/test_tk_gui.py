"""Actual widget tests; use DISPLAY=:99 on the documented Linux test display."""
import os
from pathlib import Path
import tempfile
import time
import unittest
from domino_engine import Player, deal, legal_moves
from domino_engine.controller import GameController
from domino_engine.events import EventSession


@unittest.skipUnless(os.environ.get('DISPLAY') or os.name == 'nt', 'Desktop display required (controller tests run headless)')
class TkWidgetTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from domino_engine.gui import DominoApp
        self.tk = tk
        self.root = tk.Tk()
        self.c = GameController(level=5, session=EventSession(deal(41, first=Player.ASSISTED)))
        self.app = DominoApp(self.root, self.c)
        self.root.update_idletasks()

    def tearDown(self):
        self.app.close()

    def test_hand_button_side_dialog_confirm_and_undo(self):
        initial = self.c.session.state
        move = legal_moves(initial)[0]
        button = next(b for b in self.app.hand_buttons.winfo_children() if b.cget('text') == str(move.tile))
        button.invoke()
        for child in self.root.winfo_children():
            if isinstance(child, self.tk.Toplevel):
                option = next(b for b in child.winfo_children() if b.cget('text') == str(move))
                option.invoke()
        self.assertEqual(self.c.session.state, initial)
        self.assertTrue(self.c.session.pending.legal)
        self.app.confirm_button.invoke()
        self.assertEqual(len(self.c.session.events), 1)
        self.assertEqual(len(self.c.session.state.hand(Player.ASSISTED)), 6)
        self.app.undo_button.invoke()
        self.assertEqual(self.c.session.state, initial)

    def test_actual_optional_image_preview(self):
        with tempfile.TemporaryDirectory() as tmp:
            image_path = str(Path(tmp)/'observation.png')
            image = self.tk.PhotoImage(master=self.root, width=2, height=2)
            image.put('green', to=(0,0,2,2))
            image.write(image_path, format='png')
            self.c.session.propose(legal_moves(self.c.session.state)[0], image_ref=image_path)
            self.app.render()
            self.assertIsNotNone(self.app._preview_image)
            self.assertNotEqual(str(self.app.confirm_button.cget('state')), 'disabled')

    def test_advice_is_optional_and_all_moves_available(self):
        self.c.request_decision()
        deadline = time.monotonic() + 10
        while self.c.busy and time.monotonic() < deadline:
            self.c.poll_decision()
            time.sleep(.001)
        self.app.render()
        children = self.app.moves.get_children()
        self.assertEqual(len(children), len(legal_moves(self.c.session.state)))
        self.assertTrue(all(self.app.moves.item(i, 'values')[1] == '-' for i in children))
        self.app.show_advice.set(True)
        self.app.render()
        self.assertTrue(all(self.app.moves.item(i, 'values')[1] != '-' for i in children))
