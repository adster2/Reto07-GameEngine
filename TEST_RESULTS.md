# Risultati eseguiti — 19 ottobre 2026

Validazione finale del codice: `61a4b0efedc958489eaf082acde84e57f1c573eb`. Working directory
`/workspace/Reto07-GameEngine`. I documenti e i dati sono aggiunti nel commit
successivo; non cambiano il codice validato. Comandi, exit status, tempi e SHA-256
per ogni modulo sono in [VALIDATION_RUN.json](docs/results/VALIDATION_RUN.json).
Stdout e stderr completi: [logs](docs/results/logs/).

## Gate della specifica

| Gate | Esito | Evidenza effettiva |
|---|---|---|
| 1. Tutti i test | **PASS** | 40/40, zero fallimenti, zero errori, zero skip, con display Tk Linux |
| 2. >=1.000 partite | **PASS** | 1.000 stress + 4.000 torneo: 5.000 concluse e riprodotte, zero violazioni |
| 3. Regole e transizioni | **PASS** | Test unitari, 8 scenari JSON, proprietà su partite, undo/replay e snapshot rigorosi |
| 4. Privacy / anticheat | **PASS** | Cambiati veri segreti a pari KnowledgeState: ranking identici per livelli 1–5 |
| 5. Cinque profondità | **PASS** | 26.451 decisioni del torneo, profondità completata uguale al livello, zero cutoff |
| 6. CLI e GUI | **PASS Linux** | Avvio CLI, replay, controller headless, widget reali e 5 partite Tk complete |
| 6. Launcher/resa Windows | **NOT_RUN** | Il container Linux non collauda `.cmd`, DPI, font e input del PC Windows |
| 7. Prestazioni | **PASS** | 150 posizioni, p95 186.00 ms, 150/150 a profondità 5 |
| 7. Forza strategica | **MISURATA** | Tabella sotto; target 60% contro random osservato, nessuna garanzia statistica universale |
| 8. API futura camera | **PASS contratto** | ObservedTile/ObservedScene/MoveProposal e test protocollo senza OpenCV |
| Integrazione fisica OpenCV | **NOT_RUN** | Non sono disponibili né usati i file/video locali; tracker fisico futuro separato |

Nessun gate di correttezza o prestazioni è fallito nell'ultima esecuzione.
Le prove Windows e fisiche non sono state dichiarate superate. La PR e la
pubblicazione della configurazione cloud sono azioni distinte, descritte in
PROJECT_STATUS.md; non sono un test del gioco.

## 1.000 partite stress e audit dei 4.000 incontri

```
python -m domino_engine stress --games 1000 --seed-start 20000 --output docs/results/STRESS_RESULTS.csv
python -m domino_engine audit docs/results/TOURNAMENT_EVENTS.jsonl.gz
```

Stress: seed 20000–20999, 13.126 semimosse, bot random/greedy alternati e
random/random, 1.000 replay confrontati con lo stato finale. Audit torneo:
4.000 replay, 52.662 semimosse, tutti terminali. Totale principale: **5.000
partite, 65.788 semimosse**, nessuna violazione, tessera duplicata, passaggio
illegale o deadlock rilevati. Non è una prova esaustiva di tutti gli stati possibili.

La validazione finale rigioca i transcript del torneo con il commit sopra,
compresi i nuovi controlli sui journal serializzati. La ricerca del torneo era
stata eseguita durante l'implementazione con gli stessi pesi, algoritmi numerici,
budget e seed; le successive correzioni riguardano immutabilità, controllo
snapshot e interfaccia. [EVIDENCE_INTEGRITY.json](docs/results/EVIDENCE_INTEGRITY.json)
verifica anche corrispondenza di ogni riga CSV con transcript/esito/punti/passaggi
ed equilibrio delle quattro combinazioni per ciascun deal.

## Forza strategica: valutazione indipendente

```
python -m domino_engine tournament --seeds 100 --seed-start 10000 --output docs/results
```

Per ciascuna coppia livello/bot: **400 partite su 100 deal indipendenti**,
AI nelle due posizioni e entrambi i giocatori iniziali, stessi deal per tutti
i livelli e baseline. Punti partita = vittoria 1, pareggio 0,5, sconfitta 0.
La colonna W/D/L è dal punto di vista dell'AI. Gli intervalli approssimati al 95%
sono calcolati sulle medie dei 100 deal; non si fingono 400 osservazioni
indipendenti. Confronti esplorativi, senza correzione per confronti multipli.

| Livello | W/D/L vs random | Punti vs random (IC95%) | W/D/L vs greedy | Punti vs greedy (IC95%) |
|---|---|---|---|---|
| 1 | 256/4/140 | 64.500% (59.83%–69.17%) | 211/5/184 | 53.375% (48.90%–57.85%) |
| 2 | 267/6/127 | 67.500% (63.67%–71.33%) | 235/6/159 | 59.500% (55.23%–63.77%) |
| 3 | 242/5/153 | 61.125% (56.67%–65.58%) | 221/11/168 | 56.625% (52.62%–60.63%) |
| 4 | 263/4/133 | 66.250% (61.91%–70.59%) | 228/5/167 | 57.625% (53.54%–61.71%) |
| 5 | 239/3/158 | 60.125% (55.94%–64.31%) | 219/5/176 | 55.375% (51.22%–59.53%) |

Il 60% è superato come **stima osservata** da tutti i livelli contro random;
per i livelli 1, 3 e 5 l'intervallo include valori inferiori al 60%. Il livello 2
risulta migliore in questo campione: **profondità maggiore non garantisce forza
maggiore**, per effetto di campionamento finito, policy greedy assunta e strategy
fusion. Nessuna pretesa di AI ottimale. Contro greedy il livello 1 non dimostra
un vantaggio con l'intervallo riportato. Non sono stati esclusi deal sfavorevoli.

Set di sviluppo separato: seed 1000–1024, 25 deal × 4 combinazioni × 5 livelli ×
2 bot = 1.000 partite, risultati in `docs/results/development/`. Pesi fissi
iniziali e configurazione sono stati verificati lì e non ritoccati sui seed di
test. Non è stata eseguita un'ottimizzazione automatica dei pesi; rimane una
possibile attività futura su nuovi set di sviluppo, mai sui test sopra.

26.451 decisioni AI nel torneo, 5.214.708 transizioni di ricerca, 170.832 mondi
campionati, nessun budget esaurito. Il livello 1 di norma non campiona: usa
aspettative analitiche; per un secondo passaggio terminale campiona gli esiti.
I CSV delle decisioni distinguono livello richiesto, profondità completata,
profondità visitata, nodi, campioni, limite e ms. I bot del torneo sono tutti fair.

## Prestazioni

```
python -m domino_engine benchmark --positions 150 --seed-start 30000 --output docs/results/BENCHMARK_RESULTS.csv
```

Macchina: Linux-6.18.55-x86_64-with-glibc2.41, Python 3.12.14,
AMD EPYC 9V74 80-Core Processor, **5 CPU disponibili** al processo nel container.
Tk 9.0 per le prove GUI; display Xorg dummy 1280×1024. Nessuna GPU richiesta.
150 posizioni da 150 partite indipendenti, distribuite fra apertura, metà e
fine partita; non selezionate in base al runtime. Campioni 8, budget 6.000 nodi,
1.500 ms, seed ricerca 20261019. P95 nearest-rank.

- Media: **55.86 ms**; p95: **186.00 ms**; massimo: **257.09 ms**.
- 150/150 entro 5 secondi, 150/150 ricerche completate a livello 5, zero fallback.
- Il limite temporale può rendere un ranking interrotto dipendente dal carico;
  i test riproducibili usano un budget di nodi e controllano che il tempo non scatti.

## GUI vera e comandi d'avvio

```
DISPLAY=:99 python -m unittest discover -v
python virtual_game.py --headless-smoke --level 5
DISPLAY=:99 python virtual_game.py --smoke --level 1 --seed 42
DISPLAY=:99 python virtual_game.py --smoke --level 2 --seed 42
DISPLAY=:99 python virtual_game.py --smoke --level 3 --seed 42
DISPLAY=:99 python virtual_game.py --smoke --level 4 --seed 42
DISPLAY=:99 python virtual_game.py --smoke --level 5 --seed 42
```

Tutte e cinque le partite GUI sono concluse: 13/13/13/11/11 eventi rispettivamente;
la CPU è `ai1`…`ai5` con 7/7/7/6/6 decisioni. Il collaudo aziona i pulsanti della
mano, il dialogo di lato/orientamento e Conferma, senza usare suggerimenti AI
per la parte umana. Widget testati: mano, conferma, undo, suggerimenti facoltativi
e anteprima reale PNG. Il controller verifica anche i risultati async obsoleti.
[Schermata effettiva](docs/gui-linux.png); [display usato](docs/HEADLESS_TESTING.md).

Installazione editable ripetuta con successo nella `.venv`; wheel costruita,
installata senza dipendenze né rete in un virtualenv separato sotto `/tmp`,
CLI e GUI headless eseguite fuori dal checkout. Comandi e log di packaging sono
in `docs/results/PACKAGING_VALIDATION.json` e nei relativi file in `logs/`.
Questo verifica il packaging Linux, non il launcher Windows.
