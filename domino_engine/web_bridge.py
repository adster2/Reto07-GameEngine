"""JSON bridge for the browser worker. Uses the existing referee and fair AI.

Ordinary replies contain only the human's view, legal actions and public
proposals. The explicit save/load API uses private referee logs, like the desktop.
"""
from dataclasses import asdict
import json
from .events import EventSession, ObservedScene, ObservedTile, ProposalError
from .knowledge import knowledge_for
from .simulation import StrategyBot
from .state import Player, deal
from .strategy import SearchConfig
from .tiles import Move


class WebGame:
    def __init__(self, seed=42, level=3):
        self._epoch = 0
        self._set_level(level)
        self.session = EventSession(deal(seed))
        self.ranking = None
        self.cpu_diagnostics = None

    def _set_level(self, level):
        if type(level) is not int or level not in range(1, 6):
            raise ValueError('Scegli un livello da 1 a 5.')
        self.level = level
        self.bot = StrategyBot(SearchConfig(level=level))

    @property
    def token(self):
        return f'{self._epoch}:{self.session.revision}'

    def snapshot(self):
        view = knowledge_for(self.session.state, Player.ASSISTED)
        p = self.session.pending
        result = None
        if view.terminal:
            result = {'winner': view.winner.value if view.winner else None,
                      'reason': view.reason,
                      'your_points': sum(t.points for t in view.hand),
                      'cpu_points': sum(t.points for t in self.session.state.hand(Player.OPPONENT))}
        return {'view': view.to_dict(), 'ends': list(view.ends) if view.ends else None,
                'legal_moves': [m.to_dict() for m in view.legal_moves()],
                'pending': None if p is None else {
                    'id': p.id, 'player': p.player.value, 'move': p.move.to_dict(),
                    'legal': p.legal, 'error': p.error,
                    'new_ends': list(p.new_ends) if p.new_ends else None, 'source': p.source},
                'token': self.token, 'level': self.level, 'result': result,
                'event_count': len(self.session.events),
                'ranking': [r.to_dict() for r in self.ranking.moves] if self.ranking else [],
                'advice_diagnostics': asdict(self.ranking.diagnostics) if self.ranking else None,
                'cpu_diagnostics': asdict(self.cpu_diagnostics) if self.cpu_diagnostics else None}

    def _observe(self, move, *, reread=False):
        if move.is_pass:
            if reread:
                return self.session.correct(self.session.pending.id, move)
            return self.session.propose(move, source='browser-pass')
        baseline = tuple(ObservedTile(t.left, t.right) for t in self.session.state.chain)
        scene = ObservedScene(baseline + (ObservedTile(move.tile.a, move.tile.b,
                                                       move.side, move.orientation),))
        if reread:
            return self.session.reread(self.session.pending.id, scene)
        proposal = self.session.observe(scene)
        if proposal is None:
            raise ProposalError(self.session.last_observation_error)
        return proposal

    def handle(self, request):
        if not isinstance(request, dict):
            raise ValueError('Richiesta non valida.')
        command = request.get('command')
        if command == 'view':
            return self.snapshot()
        if command == 'new_game':
            level = request.get('level', self.level)
            seed = request.get('seed', 42)
            if type(seed) is not int or not 0 <= seed <= 2**53 - 1:
                raise ValueError('Il numero della partita deve essere un intero positivo.')
            SearchConfig(level=level)  # Validate before replacing anything.
            session = EventSession(deal(seed))
            self._set_level(level)
            self.session = session
            self._epoch += 1
            self.ranking = self.cpu_diagnostics = None
            return self.snapshot()
        # Retried commits from the same game are idempotent, including after a lost reply.
        if (command == 'confirm' and str(request.get('token', '')).split(':')[0] == str(self._epoch)
                and any(e.id == request.get('proposal_id') for e in self.session.events)):
            return self.snapshot()
        if request.get('token') != self.token:
            raise ProposalError('La partita è cambiata. Aggiorna la mossa prima di confermare.')
        if command == 'set_level':
            self._set_level(request['level'])
            self.ranking = None
            self._epoch += 1
        elif command == 'propose':
            if self.session.state.turn != Player.ASSISTED:
                raise ProposalError('Attendi il tuo turno.')
            self._observe(Move.from_dict(request['move']))
        elif command == 'cpu':
            if self.session.state.turn != Player.OPPONENT or self.session.state.terminal:
                raise ProposalError('Non è il turno della CPU.')
            if self.session.pending:
                raise ProposalError('Conferma o scarta prima la proposta attuale.')
            # No referee, deal seed or opponent secrets cross this call.
            view = knowledge_for(self.session.state, Player.OPPONENT)
            move = self.bot.choose(view)
            self.cpu_diagnostics = self.bot.last_ranking.diagnostics
            self._observe(move)
        elif command == 'rank':
            if self.session.state.turn != Player.ASSISTED or self.session.state.terminal:
                raise ProposalError('I consigli sono disponibili durante il tuo turno.')
            advisor = StrategyBot(SearchConfig(level=self.level))
            advisor.choose(knowledge_for(self.session.state, Player.ASSISTED))
            self.ranking = advisor.last_ranking
        elif command in ('correct', 'reread'):
            if not self.session.pending:
                raise ProposalError('Nessuna proposta da correggere.')
            move = Move.from_dict(request['move'])
            if command == 'correct':
                self.session.correct(self.session.pending.id, move)
            else:
                self._observe(move, reread=True)
        elif command == 'confirm':
            self.session.commit(request['proposal_id'])
            self.ranking = None
        elif command == 'discard':
            if self.session.pending:
                self.session.discard(self.session.pending.id)
            self.ranking = None
        elif command == 'undo':
            self.session.undo()
            self.ranking = self.cpu_diagnostics = None
        elif command == 'save':
            return {'save': self.session.to_json(), 'level': self.level}
        elif command == 'load':
            # Construct and validate the whole replacement before publishing it.
            session = EventSession.from_json(request['save'])
            level = request.get('level', self.level)
            SearchConfig(level=level)
            self.session = session
            self._set_level(level)
            self._epoch += 1
            self.ranking = self.cpu_diagnostics = None
        else:
            raise ValueError('Comando non riconosciuto.')
        return self.snapshot()

    def handle_json(self, text):
        return json.dumps(self.handle(json.loads(text)))
