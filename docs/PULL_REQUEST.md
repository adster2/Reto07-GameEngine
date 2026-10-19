## Gioco offline umano contro CPU AI e motore domino condiviso

Il repository conteneva solo la specifica. Ora si può giocare una manche completa
contro lo StrategyEngine nella GUI Tkinter: tessere cliccabili, scelta del lato e
dell'orientamento, CPU ai livelli 1–5 e consigli all'umano facoltativi. La CPU
propone le mosse; l'utente le conferma attraverso lo stesso protocollo previsto
per la futura camera. Avvio Windows: `run_simulator.cmd`; multipiattaforma:
`python virtual_game.py --level 5` (Python 3.10+ con Tkinter).

Il core implementa il doppio-sei 7+7 senza pesca, blocchi e vittorie, stati
immutabili, proposte/correzioni/riletture, commit atomico idempotente, undo,
serializzazione/replay e otto scenari JSON. L'AI riceve soltanto KnowledgeState,
campiona mani plausibili condizionate sui passaggi e ordina tutte le mosse con
spiegazioni, budget e diagnostica. Nessun accesso alla mano vera avversaria,
agli scarti o al RNG del deal. Nessuna dipendenza da OpenCV o dai file del PC.

Validazione: 40/40 test passati senza skip su display Linux; cinque partite GUI
complete azionando mano/dialoghi/conferma; 1.000 partite stress e 4.000 incontri
indipendenti, tutti riprodotti con zero violazioni. Benchmark 150 posizioni,
profondità 5 completata in tutte; dettagli e p95 in TEST_RESULTS.md. Punti contro
random: 60,125%–67,5%; contro greedy: 53,375%–59,5%, con intervalli per deal e
senza affermare monotonicità dei livelli. CSV, transcript compressi, log, seed,
comandi e commit del codice validato inclusi in docs/results/.

Da verificare sul PC: launcher e resa Windows; integrazione fisica OpenCV e tracker
pubblico reale. La GUI e il packaging sono verificati su Linux. Le approssimazioni
della ricerca e i gate NOT_RUN sono documentati in PROJECT_STATUS.md e nei report.

Pull request aperta: https://github.com/adster2/Reto07-GameEngine/pull/1

## Aggiornamento browser

Aggiunta la versione browser, con gli stessi moduli Python eseguiti in un worker
Pyodide, interfaccia responsive, CPU fair ai livelli 1–5, conferma, consigli,
undo e save/load. Aggiunta GUIDA_GITHUB.md per il proprietario alle prime armi.
48 test passati, sei partite Chromium e 1.000 partite del protocollo JSON concluse.
Il sito generato è nel branch gh-pages. L'attivazione Pages resta da confermare:
API e dominio pubblico sono bloccati con 403 dal proxy della macchina corrente.
Istruzione per il proprietario: Settings → Pages → Deploy from a branch → gh-pages
→ / (root) → Save; il link si usa dopo la comparsa di Visit site.
