# RETO 07 — Game Engine e simulatore virtuale (mandato Codex)
Versione cloud 2.1, 19 ottobre 2026. Specifica autosufficiente. Non dipende dai file OpenCV locali.

## Scopo e comportamento obbligatorio
Implementa, non soltanto progetta, un'applicazione Python offline per sviluppare e collaudare il cervello del domino doppio-sei. Il sistema reale futuro usa un giocatore umano assistito dall'AI contro un avversario umano: il PC suggerisce una lista ordinata di mosse, l'umano le esegue fisicamente. Il simulatore virtuale sostituisce temporaneamente la camera e l'avversario fisico. Tutte le modalità devono usare lo STESSO Game Engine e le stesse regole, senza duplicazioni. Il codice sarà poi trasferito nel progetto Windows `Reto07_Domino`, quindi usa moduli Python isolati, API documentate e dipendenze leggere. Non modificare né richiedere file della pipeline di visione per implementare il simulatore.

**Mandato operativo:** analizza il repository, architetta, implementa per incrementi, esegui test, diagnostica errori, correggi e ripeti. Non fermarti alla progettazione né a una schermata dimostrativa. Non dichiarare verificato ciò che non hai eseguito. Se risorse o tempo impediscono il completamento, consegna il massimo funzionante e un elenco preciso dei gate mancanti. Non barare sui dati dei test né allentare soglie per ottenere un successo artificiale.

## Regole vincolanti
- Set unico: 28 tessere `(a,b)` con `0 <= a <= b <= 6`. Identità canonica indipendente dall'orientamento della tessera. Nessuna tessera duplicata.
- Due giocatori: `ASSISTED` e `OPPONENT`; nella GUI virtuale `OPPONENT` è simulato.
- Distribuzione casuale riproducibile: 7 tessere ciascuno, 14 fuori gioco, non pescabili. L'AI non sa quali sono fuori gioco.
- Il giocatore iniziale si sorteggia; può posare qualunque tessera sul tavolo vuoto. Da quel momento si gioca esclusivamente sulle due estremità della catena, usando un valore combaciante.
- Una mossa include tessera, estremità `LEFT`/`RIGHT` e orientamento logico. Genera entrambe le possibilità se legalmente distinte.
- Le doppie non creano diramazioni: topologia della catena sempre lineare, anche con curve e doppie orientate trasversalmente nella scena reale.
- Un solo pezzo per turno. Passaggio obbligatorio **solo se non ci sono mosse legali**. Nessuna pesca; un passaggio è una semimossa.
- Fine immediata se qualcuno svuota la mano. Altrimenti due passaggi consecutivi senza posa determinano blocco: minor somma residua vince; parità = pareggio. Un'unica manche, nessun punteggio cumulativo.
- Verifica rigorosa di turno, identità, compatibilità, passaggi, duplicati, terminalità e reversibilità delle transizioni.

## Separazione assoluta delle informazioni
L'ambiente/arbitro della simulazione conosce per necessità entrambe le mani, i 14 scarti non giocati e la verità dello stato: ciò serve SOLO a far rispettare le regole. Il cervello `StrategyEngine` riceve ESCLUSIVAMENTE una vista immutabile `KnowledgeState`: propria mano, catena, valori liberi, turno, conteggio tessere avversarie, storico pubblico, passaggi osservati, regole e configurazione di ricerca. Non riceve la vera mano avversaria, il monte escluso, riferimenti all'arbitro o un RNG correlato alla distribuzione segreta. L'avversario simulato riceve a sua volta solo la propria vista, salvo bot di controllo chiaramente marcati come oracle e mai usati per valutare prestazioni fair.
L'insieme invisibile = set 28 - mano propria - tessere pubbliche; questo comprende sia la mano avversaria sia le 14 tessere non distribuite. Distribuisci scenari plausibili senza sostituzione, condizionando dove possibile su passaggi precedenti e informazioni note al momento della decisione. Un passaggio dell'avversario (se valido nella variante) esclude dalla sua mano tessere con i valori aperti in quel momento; informazioni successive non possono essere retropropagate scorrettamente.
**Test anticheat:** a parità di `KnowledgeState`, seed e configurazione di ricerca, modificando la vera distribuzione nascosta, ranking e scelta dell'AI devono restare invariati. Il decisore deve essere puro o isolato dagli interni dell'arbitro.

## Moduli richiesti e API
Organizzazione indicativa modificabile con motivazione, con unit test autonomi:
- `domino_engine/tiles.py`: set, identità, orientamento, validazione.
- `domino_engine/rules.py`: `legal_moves(state, player)`, `apply_move(state, move)`, condizioni terminali; senza GUI/OpenCV.
- `domino_engine/state.py`: stato autorevole, catena ordinata, estremità, mani vere solo nell'arbitro virtuale, turni, passaggi e cronologia; serializzazione JSON e seed.
- `domino_engine/events.py`: proposte, correzioni, rifiuto, rilettura, conferma/commit atomico, annullamento e replay.
- `domino_engine/knowledge.py`: proiezione filtrata della vista informativa e vincoli inferiti.
- `domino_engine/strategy.py`: generazione e ranking mosse, euristica e ricerca a informazione incompleta.
- `domino_engine/simulation.py`: partite virtuali e bot con prospettive separate.
- `tests/`: unit, regressione, property/scenari, anticheat, tornei, benchmark.
- `virtual_game.py` e/o `run_simulator.cmd`: GUI giocabile con avvio documentato.
Separare API evento visivo futuro (`ObservedTile/ObservedScene/ProposedMove`) dalle transizioni del dominio. Nessuna importazione OpenCV nel core. Fornisci contratto input/output per adattatore camera futuro.

## Registrazione iniziale della mano reale
Nella futura partita fisica l'utente mostra inizialmente le sue sette tessere alla telecamera, verifica e conferma la mano, quindi le ritira per non mostrarle all'avversario. Memorizzazione della mano in `GameState`; aggiorna solo dopo conferma di una mossa propria. In simulazione la stessa situazione nasce dal deal virtuale; prevedere anche impostazione manuale per test. Il professore non ha accesso allo schermo del nostro progetto: nessun obbligo di nascondere la mano dalla GUI del giocatore assistito.

## Protocollo universale delle mosse
La camera futura rileverà autonomamente una tessera nuova confrontando scene con la baseline CONFERMATA, stimando identità, lato e collegamento, con prudenza su rumore e spostamenti. La modalità virtuale DEVE simulare questo stesso protocollo:
1. Nuova osservazione o input produce una `MoveProposal`, NON muta lo stato autorevole.
2. Mostra giocatore previsto dal turno, tessera [a|b], lato, orientamento, nuova estremità, legalità e immagine se disponibile.
3. Controlli `Conferma`, `Correggi` (valore delle due facce, lato/orientamento), `Rileggi`, `Scarta` e `Inserisci manualmente`. Il passaggio è proposto con pulsante separato e richiede conferma.
4. Ogni correzione innesca nuovamente tutte le verifiche: mossa davvero illegale non confermabile. Errori/ambiguità non aggiornano lo stato. Per la mano propria verifica presenza della tessera.
5. Il commit è atomico e idempotente: registra un solo evento, aggiorna stato, mano (se nostra), conteggio avversario, catena, estremità, storico, turno, passaggi, knowledge e fine partita.
6. `Undo` dell'ultimo evento mediante replay robusto, senza desincronizzare mano o inferenze. Se esiste una proposta pendente non applicare nuove mosse.
7. Se il riconoscitore rileva zero o più di una tessera nuova oppure la geometria è ambigua, non forzare una transizione: chiedi correzione o acquisizione.
In simulazione distingui osservazione (anche erronea), proposta, approvazione e commit; scenari di test includono lettura [3|5] al posto di [3|6], lato errato, mossa illegale reale, rilettura e doppio commit.

## Intelligenza strategica: cinque difficoltà
I livelli corrispondono rispettivamente a profondità massima **1, 2, 3, 4, 5 semimosse individuali**, passaggi inclusi; non 5 turni completi. Tutti i livelli rispettano informazione incompleta. Ogni nostro turno restituisce **tutte le mosse legali ordinate**, punteggio, raccomandazione e spiegazione comprensibile. Anche mosse sul lato opposto o con stessi valori vanno distinte quando cambiano lo stato.
Euristica iniziale: punti residui propri (minimizzare), mobilità della mano, flessibilità dei numeri residui, controllo degli estremi, probabilità di blocco dell'avversario e rischio di restare con punti alti. Gestire con premi terminali coerenti e testati. I pesi devono essere documentati e ottimizzati solo su set di sviluppo; valutazione indipendente su seed di test non usati nel tuning.
Per profondità >1 campiona possibili mani avversarie compatibili con informazioni pubbliche; simula turni in modo condizionato, con strategia avversaria plausibile, aggrega i risultati (valore atteso e facoltativamente rischio). Evita un minimax onnisciente che legga l'avversario vero. Distingui in report valutazione euristica dello stato e stima della mossa; scala punteggi uniforme, segnalando che non sono probabilità di vittoria se non calibrati. Seed di campionamento controllati. Imporre budget di tempo/nodi e fallback legale quando necessario, con diagnostica (nodi, campioni, ms, profondità raggiunta). A livello 5 evitare che esplosione combinatoria blocchi la GUI.

## Simulatore virtuale completo
- **CLI deterministica:** avvio, seed, partite, mosse/passi, salvataggio/replay; utile per debugging headless.
- **GUI Python desktop:** partita completa offline, catena, estremità, mano nostra, numero tessere avversarie senza scoprire la mano, turno, scelta livello 1–5, lista completa ordinata delle mosse con valutazioni e motivazioni, esecuzione manuale o su consiglio, bot avversario, passaggi e risultati, cronologia, undo. Una schermata realmente collegata al core, non mockup. Chiaro avvio Windows `.cmd`. UI stabile, non deve bloccarsi durante la ricerca.
- **Scenario runner:** carica stati controllati (JSON) e confronta legalità, nuova catena, proposta/commit/undo, informazione disponibile, risultato atteso. Supporta primo turno, estremità uguali, doppie, passaggi, terminali, stalli, distribuzioni limite.
- **Tornei automatici:** più seed, colori/primo turno bilanciati, bot casuale, bot greedy e livelli AI 1–5, stesse condizioni di distribuzione fair, metriche win/loss/draw, punti partita (1/0.5/0), turni, illegalità, runtime, nodi, campioni e export CSV/JSON. Non presentare come vincenti risultati basati su pochi seed.
- **Performance:** misurazione su macchina dichiarata, GUI utilizzabile, livello 5 entro 5s nel 95% delle decisioni sul set benchmark; se non riesce, indicare benchmark fallito, non manipolare la misura.
- **Qualità:** aspirare ad almeno 60% dei punti partita contro bot casuale su un set di valutazione indipendente con numerosità documentata. Obiettivo di tuning, non motivo per nascondere esiti negativi.

## Gate di accettazione e test
1. Tutti i test del repository passano (100%) e non sono stati indeboliti per farli passare.
2. Almeno **1.000 partite automatiche** riproducibili concluse senza errori di regola, tessere duplicate, passaggi illegali o deadlock.
3. Test isolati per tutte le regole incluse: apertura, lato, ribaltamento logico, doppie, no-draw, turni, passaggi, blocco, vittoria, pareggio, undo/replay.
4. Test privacy della conoscenza: modificando stati segreti a pari conoscenza l'AI produce ranking equivalente con medesimo seed.
5. Cinque livelli raggiungono (o dichiarano con diagnostica il limite di budget) profondità configurata, con passaggi conteggiati.
6. Comandi d'avvio CLI e GUI eseguiti davvero; verificare una partita completa in GUI ove possibile. Se ambiente cloud privo di display, testare logica GUI in headless e segnalare che il collaudo visuale Windows resta da eseguire.
7. Benchmark prestazioni e tornei con seed/log completi e risultati onesti. Prestazione strategica non garantita: ottimizzare e ritestare senza inventare successo.
8. Allineamento all'API futura della camera tramite adattatore documentato; nessuna integrazione fisica dichiarata completata.

## Piano autonomo di realizzazione
Task 1: repository/README/packaging, dominio tessere, regole, GameState, unit test.
Task 2: simulatore testuale, eventi confermabili, serializzazione, replay, scenario tests.
Task 3: knowledge separation, vincoli probabilistici, bot validi, tests anticheat.
Task 4: ranking euristico livello 1 e spiegazioni.
Task 5: ricerca informazione incompleta profondità 2–5 con budget, profiling, tests.
Task 6: GUI desktop e Windows launcher, partita giocabile, test UI.
Task 7: tornei massivi e benchmark; tuning senza contaminazione test; regressioni.
Task 8: documentazione per integrazione nel vecchio progetto OpenCV e report di consegna.
Esegui ogni task prima di proseguire; risolvi errori con `test → diagnosi → fix → retest`. Non chiedere autorizzazione fra task; lavorare entro limiti di sessione. Non modificare file locali del progetto visivo.

## Deliverable
- Codice sorgente funzionante, test e launcher Windows.
- `README.md` con istruzioni esatte d'installazione, avvio e verifica.
- `GAME_ENGINE_DESIGN.md` (API, architettura, distinzioni informazionali, convenzioni).
- `GAME_ENGINE_TEST_PLAN.md`, `TEST_RESULTS.md` (comandi, commit, seed, contatori, esiti).
- `BENCHMARK_RESULTS.csv`, `TOURNAMENT_RESULTS.csv` o equivalenti riproducibili.
- `VISION_INTEGRATION_CONTRACT.md` che spiega come ricevere tile observations e produrre eventi proposti senza toccare OpenCV.
- `PROJECT_STATUS.md` con attività concluse, problemi residui e cosa testare sul PC Windows.
In finale riferisci cosa è implementato e verificato, quali gate sono PASS/FAIL/NOT_RUN e con quali prove; indica onestamente se GUI Windows non verificata nel cloud.
