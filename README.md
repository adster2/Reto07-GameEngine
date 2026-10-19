# RETO 07 — Domino Game Engine

Motore Python offline per domino doppio-sei, simulatore virtuale, GUI desktop e AI
fair a cinque profondità. Si può giocare personalmente contro la CPU alimentata
dallo stesso StrategyEngine (non un bot casuale o greedy). Nessuna dipendenza da OpenCV, telecamera, rete o file del
PC. Specifica originale: [CODEX_GAME_ENGINE_SPEC.md](CODEX_GAME_ENGINE_SPEC.md).

## Giocare dal browser

La versione browser è realizzata e collaudata: usa lo stesso motore Python e la
stessa CPU ai livelli 1–5, senza installazioni sul dispositivo del giocatore.
Il sito è già preparato nel branch `gh-pages`; **l'attivazione di GitHub Pages
non è ancora confermata**, perché l'accesso API da questa macchina restituisce 403.

Per attivarlo: [Settings → Pages](https://github.com/adster2/Reto07-GameEngine/settings/pages)
→ **Deploy from a branch** → **gh-pages** → **/ (root)** → **Save**.
Quando compare **Visit site**, aprirlo per giocare. L'indirizzo previsto è
`https://adster2.github.io/Reto07-GameEngine/`; non viene presentato come già verificato.

Nella pagina clicca una tessera disponibile, scegli la posa e premi **Conferma**.
Conferma anche la proposta della CPU. I consigli per te sono facoltativi e
inizialmente nascosti. Il primo caricamento richiede la connessione e qualche
secondo per il motore Python; il gioco non richiede account o Python installato.

**Prima volta su GitHub?** Leggi [la guida semplice al nostro progetto](GUIDA_GITHUB.md).
Prove della nuova interfaccia: [WEB_TEST_RESULTS.md](WEB_TEST_RESULTS.md).
Procedure tecniche: [WEB_DEPLOYMENT.md](WEB_DEPLOYMENT.md).

## Avvio immediato

Richiede **Python 3.10+ con Tkinter** per la GUI (incluso normalmente nel Python
ufficiale Windows; su Linux il pacchetto della distribuzione è `python3-tk`).
Da questa directory, senza installare pacchetti:

```sh
python virtual_game.py --seed 42 --level 5
python -m domino_engine play --seed 42 --assisted ai5 --opponent greedy --verbose
```

Su Windows fare doppio clic su `run_simulator.cmd`, oppure:

```bat
run_simulator.cmd --seed 42 --level 5
py -3 -m unittest discover -v
```

Il launcher usa il Python selezionato da `py -3` (o `python` se `py` non c'è).
Per usare esplicitamente un virtualenv: `.venv\Scripts\python virtual_game.py`.
Per vedere subito anche i suggerimenti usare `python virtual_game.py --assist`.
Il `.cmd` e l'aspetto Windows devono ancora essere collaudati sul PC dell'utente.

Installazione opzionale dei comandi `reto07` e `reto07-gui`:

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows cmd: .venv\Scripts\activate.bat
python -m pip install --no-deps -e .
reto07 play --seed 42 --assisted ai5
reto07-gui --level 5
```

L'installazione scarica solo il backend di packaging fissato in `pyproject.toml`;
il programma e i test non hanno dipendenze pip a runtime. L'esecuzione diretta
non richiede installazione né accesso Internet.

## Giocare nella GUI

Tu sei ASSISTED: la tua mano è visibile; della CPU si mostra solo il conteggio.
La CPU usa il livello AI selezionato, propone automaticamente la propria mossa
e attende **Conferma**, secondo il protocollo universale della specifica.
Il selettore 1–5 cambia sia la CPU sia i consigli facoltativi.
L'AI calcola in un thread e restituisce **tutte** le mosse legali ordinate,
con stima della mossa, euristica immediata e motivazione. I punteggi sono utilità,
non percentuali di vittoria. I livelli 1–5 limitano la ricerca rispettivamente a
1–5 **semimosse**, inclusi i passaggi. Il pannello mostra profondità effettiva,
nodi, campioni, tempo ed eventuale limite di budget.

1. Cliccare una tessera della propria mano e scegliere la posa legale
   (lato/orientamento). In alternativa selezionare una riga e **Proponi selezionata**.
   **Mostra consigli AI** e **Proponi consiglio** sono facoltativi e inizialmente disattivati.
2. Controllare tessera, lato, orientamento, estremi e legalità. Premere **Conferma**.
3. Al turno CPU attendere la sua proposta, controllarla e premere **Conferma**.
   **Mossa avversario** permette anche di avviare esplicitamente il calcolo.
4. **Proponi passaggio** è confermabile solo quando non esistono pose legali.
5. **Correggi**, **Rileggi**, **Scarta**, **Inserisci manualmente** simulano il
   futuro protocollo della camera. Nel dialogo usare `6 3 RIGHT`, `3 6 LEFT` o `PASS`.
   Facce indicate da sinistra a destra nella catena logica; il lato è l'estremità
   di inserimento. Una lettura errata non modifica lo stato.
6. **Undo ultimo evento** ricostruisce lo stato confermato via replay. Scartare
   prima eventuali proposte pendenti. Salvataggio/caricamento ripristina la partita.
7. **Conferma mano iniziale** apre una nuova partita virtuale con sette tessere
   manuali: la mano cambia solo dopo la conferma del dialogo valido.

Non c'è pesca: 14 tessere sono fuori gioco. Due passaggi consecutivi bloccano la
manche; vince la minor somma residua, a parità pareggio. Una mano vuota vince subito.
**I replay dell'arbitro contengono mani e scarti: non passarli all'AI o alla GUI
come vista informativa.** I dati delle partite virtuali nei risultati sono pubblicati
esclusivamente come evidenza di test.

## CLI, replay e scenari

```sh
python -m domino_engine play --seed 42 --games 1 --assisted ai5 --opponent random --save local_runs/game.json --verbose
python -m domino_engine replay local_runs/game.json
python -m domino_engine scenario scenarios/01.json scenarios/02.json scenarios/03.json scenarios/04.json scenarios/05.json scenarios/06.json scenarios/07.json scenarios/08.json
python -m unittest discover -v
python virtual_game.py --headless-smoke --level 5
```

Bot: `random`, `greedy`, `ai1` … `ai5`. Il seed del deal non viene inviato ai bot.
Un replay verifica le mosse una per una e confronta lo stato finale, fallendo in
caso di corruzione. I JSON di `scenarios/` contengono stato iniziale, azioni del
protocollo e risultati attesi. Ogni aspettativa errata restituisce exit status 1.

## Misure riproducibili

```sh
python -m domino_engine stress --games 1000 --seed-start 20000 --output local_runs/STRESS_RESULTS.csv
python -m domino_engine benchmark --positions 150 --seed-start 30000 --output local_runs/BENCHMARK_RESULTS.csv
python -m domino_engine tournament --seeds 100 --seed-start 10000 --output local_runs/evaluation
```

Il torneo esegue **4.000 partite**: 5 livelli × 2 bot × 100 distribuzioni ×
2 posizioni dell'AI × 2 giocatori iniziali. Per ogni distribuzione si riusano le
stesse mani scambiando i bot, e si provano entrambi i primi giocatori.
Esporta risultati per partita, diagnostica per decisione, riepilogo con intervalli
approssimati al 95% raggruppati per deal e transcript completi JSONL compressi.
I transcript possono essere verificati senza rieseguire la ricerca con
`python -m domino_engine audit local_runs/evaluation/TOURNAMENT_EVENTS.jsonl.gz`.
Un gruppo è salvato prima di iniziare il successivo, così un'interruzione non
cancella i risultati già conclusi. Una violazione interrompe il comando con errore,
senza registrare falsamente la partita come completata.

Parametri di ricerca espliciti: `--samples 8 --max-nodes 6000 --time-ms 1500
--search-seed 20261019`. Risultati e seed di sviluppo (1000–1024), valutazione
(10000–10099), stress (20000–20999), benchmark (30000–30149) sono separati.
Ranking e mosse sono deterministici con pari vista, seed, configurazione e
budget di nodi; il limite temporale d'emergenza può interrompere a un'iterazione
diversa su macchine/carichi diversi, e viene dichiarato in diagnostica.

Per verificare realmente Tk con un display Linux disponibile:

```sh
python virtual_game.py --smoke --level 5 --seed 42
```

Il display virtuale realmente usato è documentato in [docs/HEADLESS_TESTING.md](docs/HEADLESS_TESTING.md).
`--headless-smoke` verifica il controller asincrono senza creare finestre;
`--smoke` usa Tk e aziona i pulsanti per un'intera partita. Non sostituisce il
collaudo visuale e del launcher sul PC Windows.

## Documentazione

- [Architettura, API e pesi](GAME_ENGINE_DESIGN.md)
- [Protocollo per la futura camera](VISION_INTEGRATION_CONTRACT.md)
- [Piano dei test](GAME_ENGINE_TEST_PLAN.md)
- [Risultati e gate eseguiti](TEST_RESULTS.md)
- [Stato e attività residue](PROJECT_STATUS.md)
- [Dati delle misure](docs/results/)

I file locali del progetto OpenCV non sono stati letti né modificati.
