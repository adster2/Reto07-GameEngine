"""Optional laboratory desktop using the original GUI and event controller."""
import argparse
from dataclasses import replace
import json

from domino_engine.controller import GameController
from domino_engine.gui import DominoApp
from domino_engine.knowledge import knowledge_for
from domino_engine.state import Player
from .minimax import LabConfig,MinimaxBot,MinimaxEngine
from .ismcts import MCTSConfig,ISMCTSBot,ISMCTSEngine


class LabController(GameController):
    def __init__(self,seed=42,config=MCTSConfig()):
        super().__init__(seed,config.level)
        self.lab_config = config
        self._cpu_follows_level = False
        self._configure_bot()

    def _configure_bot(self):
        config = replace(self.lab_config,level=self.level)
        self.opponent_name = f'{"ismcts" if isinstance(config,MCTSConfig) else "minimax"}{self.level}'
        self._opponent_bot = ISMCTSBot(config) if isinstance(config,MCTSConfig) else MinimaxBot(config)

    def request_decision(self):
        if self.busy or self.session.pending or self.session.state.terminal:
            return False
        view = knowledge_for(self.session.state,self.session.state.turn)
        self._token = (id(self.session),self.session.revision,self.level,self._generation)
        if view.observer == Player.ASSISTED:
            cfg = replace(self.lab_config,level=self.level,
                          seed=self.lab_config.seed+1009*len(view.history)+view.observer.index)
            engine = ISMCTSEngine(cfg) if isinstance(cfg,MCTSConfig) else MinimaxEngine(cfg)
            self._future = self._pool.submit(engine.rank,view)
        else:
            self._future = self._pool.submit(self._opponent_bot.choose,view)
        return True

    def set_level(self,level):
        super().set_level(level)
        self._configure_bot()

    def replace_session(self,session):
        self.session = session
        self.ranking = None
        self._generation += 1
        self._configure_bot()


def main():
    parser = argparse.ArgumentParser(description='GUI del laboratorio, separata dal sito consegnato')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--level',type=int,default=3)
    parser.add_argument('--samples',type=int)
    parser.add_argument('--algorithm',choices=['ismcts','minimax'],default='ismcts')
    parser.add_argument('--smoke',action='store_true')
    args = parser.parse_args()
    import tkinter as tk
    root = tk.Tk()
    config_class = MCTSConfig if args.algorithm=='ismcts' else LabConfig
    options = {'level':args.level}
    if args.samples is not None: options['samples'] = args.samples
    controller = LabController(args.seed,config_class(**options))
    app = DominoApp(root,controller,smoke=args.smoke)
    root.title(f'RETO 07 · Laboratorio {args.algorithm} — versione sperimentale')
    root.mainloop()
    if args.smoke:
        print(json.dumps({'complete_game':app.smoke_completed,'error':app.smoke_error,
                          'events':len(controller.session.events),'cpu_decisions':controller.cpu_decisions,
                          'policy':controller.opponent_name}))
        return 0 if app.smoke_completed and not app.smoke_error else 1
    return 0


if __name__ == '__main__': raise SystemExit(main())
