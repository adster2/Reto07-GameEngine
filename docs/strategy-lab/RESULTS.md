# Laboratorio strategico — primo esperimento, 19 ottobre 2026

La consegna accettata è congelata nel tag `consegna-v1.0`, ramo
`release/consegna-v1`. I 133 file originali sono byte-identici e il sito
`gh-pages` rimane al commit `0192cb9654acfa381835f70c457e35dadffeb088`.
[FROZEN_CHECK.json](FROZEN_CHECK.json) registra anche i riferimenti remoti.

**Decisione: non promuovere ancora il nuovo motore sul sito della consegna.**
Questo primo ISMCTS non dimostra un vantaggio sul vecchio livello 2 o 3.
L'implementazione di un algoritmo più adatto alle informazioni nascoste e di
un'euristica più ricca non basta, da sola, a dimostrare maggiore forza.

## Verifiche effettivamente eseguite

- Suite Python completa con display Linux: **70/70 PASS**, zero fallimenti,
  errori o skip. Include i test originali, 13 test del modello/minimax e 9 di
  ISMCTS/tattiche. Test anticheat con mani reali nascoste diverse a pari conoscenza;
  campionamento combinatorio verificato, alpha-beta confrontato con minimax
  esaustivo, vincoli dei passaggi e policy dei rollout limitate a KnowledgeState.
- GUI Linux del laboratorio ISMCTS: tre partite complete attraverso i widget,
  seed 42, livelli 1/3/5, rispettivamente 15/8/13 eventi. La nuova CPU è effettiva.
- Import CLI di un salvataggio del browser originale: **PASS**.
- Sviluppo minimax: 480 partite complessive su distribuzioni 70000–70019,
  livelli 2/3/4/5, con configurazioni e risultati conservati, compresi quelli
  sfavorevoli. Nessuna superiorità generale dimostrata; metodo conservato come
  controllo, non principale. I pesi non sono stati ottimizzati.
- Sviluppo ISMCTS: 240 partite sugli stessi seed di sviluppo, poi configurazione
  congelata prima della valutazione indipendente. Nessun peso modificato sui
  seed di valutazione.
- Valutazione indipendente ISMCTS: **1.344 partite**, 84 distribuzioni nuove
  (80000–80083), quattro combinazioni di posto e primo giocatore per ogni
  avversario. Tutte passano dall'arbitro e dal protocollo EventSession originali.
- **17.790 semimosse**. zero violazioni rilevate. 1344 replay verificati.
- Audit separato: hash di tutti i file, equilibrio delle combinazioni,
  corrispondenza fra CSV e journal, esiti, punti, passaggi e diagnostiche per
  decisione verificati. Non è una prova esaustiva di tutti gli stati possibili.

## Risultati indipendenti

Punti partita: vittoria 1, pareggio 0,5, sconfitta 0. W/D/L dal punto di vista
ISMCTS. Ogni riga comprende 336 partite su **84 deal indipendenti**; gli
intervalli approssimati al 95% sono calcolati sulle medie dei deal. Confronti
esplorativi, senza correzione per confronti multipli.

| Avversario | Partite | W/D/L | Punti partita | IC95% per deal |
|---|---:|---|---:|---|
| Consegna livello 2 | 336 | 165/0/171 | 49.11% | 44.03%–54.19% |
| Consegna livello 3 | 336 | 172/7/157 | 52.23% | 47.23%–57.23% |
| Greedy | 336 | 177/5/154 | 53.42% | 48.51%–58.34% |
| Casuale | 336 | 227/4/105 | 68.15% | 63.27%–73.04% |

Gli intervalli contro livello 2, livello 3 e greedy comprendono il 50%: non si
conclude un vantaggio statisticamente dimostrato. Contro random il vantaggio è
osservato; questo non equivale a prevedere una vittoria contro un essere umano.
Le percentuali storiche su altri seed non vanno confrontate come un esperimento
appaiato. Non sono state escluse sconfitte o distribuzioni sfavorevoli.

## Configurazione e tempi

Sorgenti del metodo valutato: `59e82196a639c37969e623e2ed34dd3484aa3cee`.
Gli hash sono in [validation/VALIDATION.json](validation/VALIDATION.json).
I commit successivi aggiungono evidenze, un auditor verificato sui dati reali,
chiarimenti documentali e la rimozione di una riga vuota finale in `__init__`;
non cambiano l'algoritmo sottoposto alla valutazione indipendente.

Configurazione: albero esplicito di profondità 3, pool massimo di 128 mani
compatibili distinte, 256 simulazioni richieste per le decisioni con alternative
(una per quelle obbligate), 30.000 transizioni e 1.500 ms di budget. UCT 1,0.
Le simulazioni proseguono fino al terminale con un limite di 44 semimosse.
`completed_depth=44` significa che la valutazione ha coperto le mosse iniziali
con simulazioni complete; non che l'albero esplicito sia profondo 44.

8923 decisioni; zero budget esauriti. P95 decisionale CPython: **504.52 ms**.
È il tempo osservato durante l'arena a quattro processi sul cloud Linux,
non un benchmark Pyodide o una garanzia sul PC del professore. Configurazione,
versioni e comando sono in [EVALUATION.json](EVALUATION.json).

## Limiti e prossime ipotesi

Le probabilità della mano sono uniformi e condizionate a tessere visibili e
passaggi obbligatori, senza modello appreso delle pose volontarie. Le 14 escluse
impediscono di identificare la mano avversaria soltanto contando le tessere viste.
SO-ISMCTS condivide l'albero fra ipotesi, ma rimane approssimato: qualità e
quantità dei rollout, modello dell'avversario e allocazione del budget incidono.
Non risolve l'equilibrio bayesiano del domino.

I principi forniti dall'utente sono fattori condizionati, non comandi assoluti.
Il blocco ai punti usa un conteggio combinatorio esatto per la priorità iniziale,
mentre i rollout usano una stima meno costosa. Pesi e policy sono iniziali.
Servono esperimenti di ablazione e tuning sui soli dati di sviluppo; un'eventuale
prossima versione deve essere valutata su un nuovo insieme di seed, perché
80000–80083 sono ora stati osservati e non sono più un nuovo holdout.

**NOT_RUN:** laboratorio nel browser/Pyodide, Windows fisico, Safari/Firefox,
integrazione OpenCV. Il sito della consegna resta la versione già accettata.

## Riproduzione e dati

Dalla radice del repository, usando nuove directory di output:

```sh
DISPLAY=:101 python -m unittest discover -v
python -m strategy_lab arena --deals 84 --seed-start 80000 --opponents ai2 ai3 greedy random --workers 4 --output local_runs/lab-reproduction
python -m strategy_lab.audit local_runs/lab-reproduction
```

Per il display seguire la procedura esistente in `docs/HEADLESS_TESTING.md`,
scegliendo il display effettivamente disponibile. Nessun servizio permanente
richiesto. I risultati già salvati non vengono sovrascritti dall'arena.

- [Holdout: riepilogo](ismcts-holdout/SUMMARY.json), [partite](ismcts-holdout/GAMES.csv),
  [decisioni](ismcts-holdout/DECISIONS.csv), [journal completi](ismcts-holdout/EVENTS.jsonl.gz),
  [audit](ismcts-holdout/AUDIT.json).
- [Sviluppo ISMCTS](ismcts-development/SUMMARY.json).
- Sviluppo minimax: [livello 2](minimax-development-level2/SUMMARY.json),
  [livello 3](minimax-development-level3/SUMMARY.json),
  [livello 4](minimax-development-level4/SUMMARY.json),
  [livello 5](minimax-development-level5/SUMMARY.json).
- [Log e hash dei sorgenti](validation/VALIDATION.json).

Il ramo `experiment/strategy-lab` è caricato su GitHub. L'apertura automatica
ed effettiva della nuova draft PR è **BLOCKED**: il proxy restituisce
`Post https://api.github.com/graphql: Forbidden`.
[GITHUB_DRAFT_PR.json](GITHUB_DRAFT_PR.json) conserva l'esito, senza dichiarare
creata una PR inesistente. La PR originale della consegna non viene modificata.
