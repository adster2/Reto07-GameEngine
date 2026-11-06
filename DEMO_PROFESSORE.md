# RETO 07 — Demo per il professore

**6 novembre 2026.** Screenshot reali del simulatore browser consegnato,
tag `consegna-v1.0`, commit `53b349bc82db48d44deeeed7df5d2c760755b787`.
Motore, regole, strategia e interfaccia accettati sono rimasti invariati.

## Caratteristiche implementate

- Domino doppio-sei: due giocatori, sette tessere ciascuno, 14 escluse,
  nessuna pesca; passaggi obbligatori, vittoria e blocco ai punti.
- AI che usa solo mano propria e fatti pubblici, con inferenze dai passaggi
  e valutazione di mani avversarie compatibili.
- Cinque livelli da una a cinque semimosse, budget di tempo/nodi,
  classifica di tutte le mosse legali e spiegazioni.
- CLI, desktop Tk e browser con lo stesso cervello; catena con curve,
  doppie trasversali, conferme, recupero errori, undo, salvataggi e replay.

## Percorso visivo

Nove PNG integrali di Chromium, senza ritocchi o mockup. Seed **43**, livello
**3**, clic automatizzati sui controlli reali; la parte umana gioca la tessera
legale con più punti. La demo non misura la forza contro persone.

| Screenshot | Contesto |
|---|---|
| [Mano iniziale](docs/demo-professore/01-mano-iniziale.png) | Sette tessere proprie, sette CPU coperte, tavolo vuoto |
| [Partita in corso](docs/demo-professore/02-partita-in-corso.png) | Due pose confermate, estremi 2 e 6, sei tessere per giocatore |
| [Classifica e consiglio AI](docs/demo-professore/03-classifica-consiglio-ai.png) | Due mosse ordinate e spiegate; prima scelta 1–6 a destra |
| [Cinque livelli](docs/demo-professore/README.md#cinque-livelli) | Cinque immagini del selettore originale impostato da 1 a 5 |
| [Fine partita](docs/demo-professore/05-fine-partita.png) | Blocco dopo due passaggi consecutivi; CPU vincente, 5 punti contro 16 |

[Galleria, didascalie e procedura riproducibile](docs/demo-professore/README.md).

## Principali risultati verificati

Campagne storiche del **19 ottobre 2026**, non rieseguite per questa demo:

| Verifica | Risultato documentato |
|---|---|
| Stress dominio + torneo indipendente | 5.000 partite, 65.788 semimosse, zero violazioni rilevate |
| Stress bridge JSON browser | 1.000 partite, 12.966 semimosse, zero violazioni |
| Totale | **6.000 partite, 78.754 semimosse**, replay verificati |
| Suite Python con display Linux | **48/48 PASS**, zero skip |
| Livello 2 contro casuale / greedy | **67,5% / 59,5% dei punti partita** |
| Benchmark CPython livello 5 | 150 posizioni, **p95 186 ms**, tutte a profondità 5 |

Punti partita: vittoria 1, pareggio 0,5, sconfitta 0. Ogni confronto strategico
usa 400 partite su 100 distribuzioni, con posti e primo giocatore bilanciati.
Il livello 2 è il migliore nel campione. Benchmark su Linux, AMD EPYC,
cinque CPU disponibili; non garantisce gli stessi tempi su Windows.
Metodi, intervalli di confidenza e limiti: [TEST_RESULTS.md](TEST_RESULTS.md)
e [WEB_TEST_RESULTS.md](WEB_TEST_RESULTS.md). Lo stress JSON non equivale
a 1.000 partite azionate dentro Chromium.

**Oggi:** una partita browser completa, nove screenshot, otto test bridge
superati senza skip, zero errori pagina/console; 133 file della consegna
confrontati byte per byte senza differenze.
[Provenienza](docs/demo-professore/PROVENIENZA.json) e
[verifiche del materiale](docs/demo-professore/VERIFICA_MATERIALE.json).

## Limiti e integrazione OpenCV

L'AI è approssimata e può perdere; maggiore profondità non garantisce maggiore
forza. I punteggi sono utilità, non probabilità di vittoria. La mano avversaria
rimane incerta anche contando le tessere, perché 14 sono escluse.

**L'integrazione fisica OpenCV non è completata né collaudata nel cloud.**
Esiste il [contratto](VISION_INTEGRATION_CONTRACT.md); sul PC servono ancora
adattatore visivo, tracker fisico con sole informazioni conosciute e prove con
camera e operatore. Passaggi avversari e punti al blocco richiedono conferma umana.
[Mandato per l'agente locale](ISTRUZIONI_AGENTE_LOCALE.md).

Le immagini provengono da una build locale del simulatore. Windows, camera reale,
Firefox, Safari, telefono fisico e verifica del sito pubblico sono **NOT_RUN**
in questa acquisizione.
