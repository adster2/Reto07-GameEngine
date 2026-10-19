"""Offline Tk desktop simulator. All mutations go through EventSession."""
import argparse
from dataclasses import asdict
import json
import time
from .controller import GameController
from .events import EventSession, ProposalError
from .rules import IllegalMove
from .state import Player, deal
from .tiles import Move, OrientedTile, Side, Tile


def headless_smoke(seed=42, level=5, opponent=None):
    """Play a full match through the GUI controller, including asynchronous polling."""
    controller = GameController(seed, level, opponent)
    deadline = time.monotonic() + 60
    try:
        while not controller.session.state.terminal:
            if time.monotonic() > deadline:
                raise RuntimeError('GUI controller smoke timed out')
            if controller.session.pending:
                controller.confirm()
            elif controller.ranking and controller.session.state.turn == Player.ASSISTED:
                controller.propose_observation(controller.ranking.recommendation)
            elif controller.busy:
                controller.poll_decision()
                time.sleep(.001)
            else:
                controller.request_decision()
        original = controller.session.state
        replay = EventSession.from_json(controller.session.to_json())
        if original != replay.state:
            raise AssertionError('GUI replay mismatch')
        return {"mode": "headless-controller", "seed": seed, "level": level,
                "events": len(controller.session.events), "terminal": True,
                "winner": original.winner.value if original.winner else None,
                "cpu_policy": controller.opponent_name, "cpu_decisions": controller.cpu_decisions}
    finally:
        controller.close()


class DominoApp:
    def __init__(self, root, controller, *, smoke=False, assist=False):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.root, self.controller = root, controller
        self.smoke = smoke
        self.smoke_completed = False
        self.smoke_error = None
        self.started = time.monotonic()
        root.title('RETO 07 · Domino doppio-sei')
        root.geometry('1150x850')
        root.minsize(900, 700)
        root.protocol('WM_DELETE_WINDOW', self.close)
        outer = ttk.Frame(root, padding=12)
        outer.pack(fill='both', expand=True)
        toolbar = ttk.Frame(outer)
        toolbar.pack(fill='x')
        for label, command in [('Nuova partita', self.new_game), ('Conferma mano iniziale', self.manual_hand),
                               ('Salva replay', self.save), ('Carica replay', self.load)]:
            ttk.Button(toolbar, text=label, command=lambda c=command: self.guard(c)).pack(side='left', padx=3)
        ttk.Label(toolbar, text='Livello CPU e consiglio:').pack(side='left', padx=(12, 3))
        self.level = tk.StringVar(value=str(controller.level))
        selector = ttk.Combobox(toolbar, textvariable=self.level, values=('1','2','3','4','5'), width=3, state='readonly')
        selector.pack(side='left')
        selector.bind('<<ComboboxSelected>>', lambda _: self.change_level())
        self.status = ttk.Label(outer, font=('Segoe UI', 12, 'bold'))
        self.status.pack(fill='x', pady=10)
        hand_area = ttk.LabelFrame(outer, text='La tua mano · clicca una tessera per giocare')
        hand_area.pack(fill='x', pady=5)
        self.hand = ttk.Label(hand_area)
        self.hand.pack(anchor='w', padx=5)
        self.hand_buttons = ttk.Frame(hand_area)
        self.hand_buttons.pack(fill='x', padx=4, pady=5)
        chain_frame = ttk.LabelFrame(outer, text='Catena lineare · scorrimento orizzontale')
        chain_frame.pack(fill='x', pady=6)
        self.canvas = tk.Canvas(chain_frame, height=88, background='#173b42', highlightthickness=0)
        self.canvas.pack(fill='x')
        scroll = ttk.Scrollbar(chain_frame, orient='horizontal', command=self.canvas.xview)
        scroll.pack(fill='x')
        self.canvas.configure(xscrollcommand=scroll.set)
        self.show_advice = tk.BooleanVar(value=assist)
        ttk.Checkbutton(outer, text='Mostra consigli AI (facoltativo durante la sfida)',
                        variable=self.show_advice, command=self.render).pack(anchor='w')
        self.move_heading = ttk.Label(outer)
        self.move_heading.pack(anchor='w')
        self.moves = ttk.Treeview(outer, columns=('move','estimate','heuristic','reason'), show='headings', height=9)
        for name, title, width in [('move','Mossa e orientamento',235), ('estimate','Stima mossa',95),
                                   ('heuristic','Euristica',85), ('reason','Motivo',580)]:
            self.moves.heading(name, text=title)
            self.moves.column(name, width=width, minwidth=60, stretch=name == 'reason')
        self.moves.pack(fill='both', expand=True)
        self.moves.bind('<Double-1>', lambda _: self.guard(self.propose_selected))
        actions = ttk.Frame(outer)
        actions.pack(fill='x', pady=8)
        self.action_buttons = {}
        for key, label, command in [('selected','Proponi selezionata',self.propose_selected),
                                    ('advice','Proponi consiglio',self.propose_advice),
                                    ('bot','Mossa avversario',self.opponent),
                                    ('pass','Proponi passaggio',lambda: controller.session.propose(Move())),
                                    ('manual','Inserisci manualmente',lambda: self.edit('manual'))]:
            button = ttk.Button(actions, text=label, command=lambda c=command: self.guard(c))
            button.pack(side='left', padx=3)
            self.action_buttons[key] = button
        proposal_frame = ttk.LabelFrame(outer, text='Osservazione / proposta · nessuna modifica prima della conferma')
        proposal_frame.pack(fill='x', pady=4)
        self.proposal_label = ttk.Label(proposal_frame, wraplength=1050)
        self.proposal_label.pack(anchor='w', padx=8, pady=5)
        self.preview_label = ttk.Label(proposal_frame)
        self.preview_label.pack(anchor='w', padx=8)
        self._preview_ref = None
        self._preview_image = None
        confirmation = ttk.Frame(proposal_frame)
        confirmation.pack(fill='x', padx=5, pady=5)
        self.confirm_button = ttk.Button(confirmation, text='Conferma', command=lambda: self.guard(controller.confirm))
        self.confirm_button.pack(side='left', padx=3)
        self.pending_buttons = []
        for label, command in [('Correggi',lambda: self.edit('correct')), ('Rileggi',lambda: self.edit('reread')),
                               ('Scarta',controller.discard)]:
            b = ttk.Button(confirmation, text=label, command=lambda c=command: self.guard(c))
            b.pack(side='left', padx=3)
            self.pending_buttons.append(b)
        self.undo_button = ttk.Button(confirmation, text='Undo ultimo evento', command=lambda: self.guard(controller.undo))
        self.undo_button.pack(side='left', padx=20)
        self.diag = ttk.Label(outer)
        self.diag.pack(fill='x', pady=4)
        ttk.Label(outer, text='Cronologia pubblica').pack(anchor='w')
        self.history = tk.Text(outer, height=7, font=('Consolas',10), state='disabled')
        self.history.pack(fill='x')
        self.message = ttk.Label(outer, foreground='#a02323', wraplength=1050)
        self.message.pack(fill='x', pady=4)
        self.render()
        root.after(30, self.tick)

    def guard(self, command):
        try:
            command()
            self.message.configure(text='')
        except (ValueError, RuntimeError, OSError) as exc:
            self.message.configure(text=str(exc))
            if self.smoke:
                self.smoke_error = str(exc)
        self.render()

    def render(self):
        c, v = self.controller, self.controller.snapshot()
        p = c.session.pending
        outcome = 'PAREGGIO' if v.winner is None else 'HAI VINTO' if v.winner == Player.ASSISTED else 'HA VINTO LA CPU'
        result = f' · {outcome} ({v.reason})' if v.terminal else ''
        actor = 'TU (ASSISTED)' if v.turn == Player.ASSISTED else 'CPU (OPPONENT)'
        self.status.configure(text=f'Turno: {actor} · CPU {c.opponent_name}: {v.opponent_count} tessere · Estremi: {v.ends}{result}')
        self.hand.configure(text=f'{len(v.hand)} tessere · {sum(t.points for t in v.hand)} punti residui')
        for widget in self.hand_buttons.winfo_children(): widget.destroy()
        playable = {m.tile for m in v.legal_moves() if not m.is_pass}
        for tile in v.hand:
            button = self.ttk.Button(self.hand_buttons, text=str(tile), width=7,
                command=lambda t=tile: self.guard(lambda: self.choose_tile(t)))
            button.pack(side='left', padx=3)
            button.configure(state='normal' if tile in playable and not p else 'disabled')
        self.canvas.delete('all')
        for index, tile in enumerate(v.chain):
            x = 12 + index * 74
            self.canvas.create_rectangle(x, 14, x+66, 70, fill='#fff8e5', outline='#e2c999', width=2)
            self.canvas.create_line(x+33, 18, x+33, 66, fill='#173b42')
            self.canvas.create_text(x+17, 42, text=str(tile.left), fill='#173b42', font=('Consolas',18,'bold'))
            self.canvas.create_text(x+49, 42, text=str(tile.right), fill='#173b42', font=('Consolas',18,'bold'))
        self.canvas.configure(scrollregion=(0,0,max(1100,len(v.chain)*74+24),88))
        # Preserve selection while refreshing after timer events.
        selected = self.moves.selection()
        self.moves.delete(*self.moves.get_children())
        if c.ranking and v.turn == Player.ASSISTED:
            ordered = list(enumerate(c.ranking.moves))
            if not self.show_advice.get(): ordered.sort(key=lambda item: str(item[1].move))
            for i, rank in ordered:
                self.moves.insert('', 'end', iid=str(i), values=(str(rank.move),
                    f'{rank.score:.2f}' if self.show_advice.get() else '-',
                    f'{rank.heuristic_score:.2f}' if self.show_advice.get() else '-',
                    rank.explanation if self.show_advice.get() else ''))
            if selected and selected[0] in self.moves.get_children(): self.moves.selection_set(selected[0])
        self.move_heading.configure(text=('Tutte le mosse ordinate · utilità, non probabilità di vittoria'
                                    if self.show_advice.get() else 'Mosse disponibili · consigli nascosti durante la sfida'))
        if p:
            self.proposal_label.configure(text=f'{p.player.value} · {p.move} · Nuovi estremi: {p.new_ends} · '
                f'{"LEGALE" if p.legal else "ILLEGALE: " + str(p.error)} · fonte: {p.source}'
                + (f' · immagine: {p.image_ref}' if p.image_ref else ''))
        else:
            self.proposal_label.configure(text='Nessuna proposta. Osservazioni e correzioni non modificano la partita.')
        image_ref = p.image_ref if p else None
        if image_ref != self._preview_ref:
            self._preview_ref = image_ref
            self._preview_image = None
            self.preview_label.configure(image='', text='')
            if image_ref:
                try:
                    image = self.tk.PhotoImage(file=image_ref)
                    scale = max(1, (image.width()+599)//600, (image.height()+159)//160)
                    self._preview_image = image.subsample(scale, scale)
                    self.preview_label.configure(image=self._preview_image)
                except self.tk.TclError:
                    self.preview_label.configure(text='Anteprima non disponibile (PNG/GIF richiesto).')
        self.confirm_button.configure(state='normal' if p and p.legal else 'disabled')
        for b in self.pending_buttons: b.configure(state='normal' if p else 'disabled')
        enabled = not p and not v.terminal
        for key, b in self.action_buttons.items():
            ok = enabled
            if key in ('selected','advice'): ok = ok and v.turn == Player.ASSISTED and c.ranking is not None
            if key == 'advice': ok = ok and (self.show_advice.get() or self.smoke)
            if key == 'bot': ok = ok and v.turn == Player.OPPONENT and not c.busy
            b.configure(state='normal' if ok else 'disabled')
        self.undo_button.configure(state='normal' if c.session.events and not p else 'disabled')
        text = '\n'.join(f'{i+1:02d}. {e.player.value}: {e.move}' for i,e in enumerate(c.session.events))
        self.history.configure(state='normal')
        self.history.delete('1.0','end')
        self.history.insert('end',text)
        self.history.see('end')
        self.history.configure(state='disabled')
        d = c.last_cpu_diagnostics if v.turn == Player.OPPONENT else c.last_diagnostics
        self.diag.configure(text=('Ricerca in corso... UI disponibile' if c.busy else
            f'Profondità {d.completed_depth}/{d.requested_depth}, nodi {d.nodes}, campioni {d.samples}, '
            f'{d.elapsed_ms:.1f} ms, limite: {d.limit or "nessuno"}' if d else ''))

    def tick(self):
        c = self.controller
        try:
            event = c.poll_decision()
            if event: self.render()
            if not c.busy and not c.session.pending and not c.session.state.terminal:
                if c.session.state.turn == Player.OPPONENT or c.ranking is None:
                    c.request_decision()
                    self.render()
            if self.smoke:
                if time.monotonic() - self.started > 60: raise RuntimeError('Tk GUI smoke timed out')
                if c.session.state.terminal:
                    self.smoke_completed = True
                    self.root.after(50, self.close)
                    return
                if c.session.pending: self.confirm_button.invoke()
                elif c.session.state.turn == Player.ASSISTED and c.ranking:
                    # Exercise the human hand buttons and side/orientation dialog.
                    legal = c.snapshot().legal_moves()
                    move = legal[0]
                    if move.is_pass:
                        self.action_buttons["pass"].invoke()
                    else:
                        button = next(b for b in self.hand_buttons.winfo_children() if b.cget('text') == str(move.tile))
                        button.invoke()
                        for child in self.root.winfo_children():
                            if isinstance(child, self.tk.Toplevel):
                                option = next(b for b in child.winfo_children()
                                              if isinstance(b, self.ttk.Button) and b.cget('text') == str(move))
                                option.invoke()
                elif c.session.state.turn == Player.OPPONENT and not c.busy: self.action_buttons["bot"].invoke()
                if self.smoke_error: raise RuntimeError(self.smoke_error)
        except Exception as exc:
            self.message.configure(text=f'Errore: {exc}')
            if self.smoke:
                self.smoke_error = str(exc)
                self.close()
                return
        self.root.after(30, self.tick)

    def choose_tile(self, tile):
        moves = [m for m in self.controller.snapshot().legal_moves() if m.tile == tile]
        if not moves: raise IllegalMove('Questa tessera non è giocabile')
        if len(moves) == 1:
            self.controller.propose_observation(moves[0])
            return
        dialog = self.tk.Toplevel(self.root)
        dialog.title('Scegli lato e orientamento')
        dialog.transient(self.root)
        dialog.grab_set()
        self.ttk.Label(dialog, text=f'Tessera {tile}: scegli una posa legale').pack(padx=15, pady=10)
        def select(move):
            dialog.destroy()
            self.guard(lambda: self.controller.propose_observation(move))
        for move in moves:
            self.ttk.Button(dialog, text=str(move), command=lambda m=move: select(m)).pack(fill='x', padx=15, pady=4)
        self.ttk.Button(dialog, text='Annulla', command=dialog.destroy).pack(padx=15, pady=10)

    def propose_selected(self):
        selected = self.moves.selection()
        if not selected: raise ProposalError('Seleziona una mossa')
        self.controller.propose_observation(self.controller.ranking.moves[int(selected[0])].move)

    def propose_advice(self):
        if not self.controller.ranking: raise ProposalError('Attendi la ricerca')
        self.controller.propose_observation(self.controller.ranking.recommendation)

    def opponent(self):
        if self.controller.session.state.turn != Player.OPPONENT: raise ProposalError('Non è il turno avversario')
        self.controller.request_decision()

    def change_level(self):
        self.controller.set_level(int(self.level.get()))
        self.render()

    def edit(self, mode):
        from tkinter import simpledialog
        p = self.controller.session.pending
        default = '' if p is None or p.move.is_pass else f'{p.move.orientation.left} {p.move.orientation.right} {p.move.side.value}'
        answer = simpledialog.askstring('Rilettura virtuale' if mode == 'reread' else 'Tessera e orientamento',
            'Faccia sinistra, faccia destra, lato LEFT/RIGHT. Esempio: 6 3 RIGHT\nOppure PASS (sarà validato).',
            initialvalue=default, parent=self.root)
        if answer is None: return
        if answer.strip().upper() == 'PASS': move = Move()
        else:
            a,b,side = answer.upper().split()
            oriented = OrientedTile(int(a),int(b))
            move = Move(oriented.tile, Side(side), oriented)
        if mode == 'correct': self.controller.session.correct(p.id, move)
        elif mode == 'reread': self.controller.reread(move)
        else: self.controller.propose_observation(move)

    def manual_hand(self):
        from tkinter import simpledialog
        answer = simpledialog.askstring('Conferma sette tessere iniziali',
            'Nuova partita virtuale. Inserisci e conferma sette tessere diverse:\n0-0 0-1 1-2 2-3 3-4 4-5 5-6', parent=self.root)
        if answer is not None:
            tiles = [Tile(*(int(v) for v in part.split('-'))) for part in answer.split()]
            self.controller.register_manual_hand(tiles)

    def new_game(self):
        from tkinter import simpledialog
        seed = simpledialog.askinteger('Nuova partita', 'Seed riproducibile:', initialvalue=42, parent=self.root)
        if seed is not None: self.controller.replace_session(EventSession(deal(seed)))

    def save(self):
        from tkinter import filedialog
        from pathlib import Path
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension='.json', title='Replay PRIVATO arbitro (include mani)')
        if path: Path(path).write_text(self.controller.session.to_json(), encoding='utf-8')

    def load(self):
        from tkinter import filedialog
        from pathlib import Path
        path = filedialog.askopenfilename(parent=self.root, filetypes=[('JSON','*.json')])
        if path: self.controller.replace_session(EventSession.from_json(Path(path).read_text(encoding='utf-8')))

    def close(self):
        self.controller.close()
        self.root.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--level', type=int, choices=range(1,6), default=3)
    parser.add_argument('--opponent', choices=['random','greedy','ai1','ai2','ai3','ai4','ai5'], default=None)
    parser.add_argument('--assist', action='store_true', help='Show AI advice for the human player')
    parser.add_argument('--headless-smoke', action='store_true')
    parser.add_argument('--smoke', action='store_true', help='Exercise actual Tk callbacks for one full match (display required)')
    args = parser.parse_args(argv)
    if args.headless_smoke:
        print(json.dumps(headless_smoke(args.seed, args.level, args.opponent)))
        return 0
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f'Display non disponibile: {exc}. Usa --headless-smoke per la logica GUI.')
        return 1
    c = GameController(args.seed, args.level, args.opponent)
    app = DominoApp(root, c, smoke=args.smoke, assist=args.assist)
    root.mainloop()
    if args.smoke:
        print(json.dumps({"mode": "tk-gui", "complete_game": app.smoke_completed,
                          "events": len(c.session.events), "error": app.smoke_error,
                          "cpu_policy": c.opponent_name, "cpu_decisions": c.cpu_decisions}))
        return 0 if app.smoke_completed and not app.smoke_error else 1
    return 0
