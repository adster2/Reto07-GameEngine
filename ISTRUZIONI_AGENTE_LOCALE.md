# Mandato operativo per l'agente AI sul PC — RETO 07

Questo documento è il mandato da eseguire, non una proposta da ripianificare.
Il proprietario vuole unire il Game Engine cloud già accettato al progetto
OpenCV sul proprio PC Windows, denominato `Reto07_Domino`. I percorsi reali,
i file della pipeline e il suo framework GUI devono essere scoperti localmente.

## 1. Obiettivo e limiti del mandato

Realizza un'app funzionante per **umano assistito dall'AI contro avversario
umano**, con lettura iniziale della mano propria e lettura del tavolo tramite
la pipeline OpenCV esistente. L'AI propone tutte le mosse legali ordinate;
l'operatore esegue fisicamente quella scelta. Osservazioni ed esecuzioni
diventano eventi della partita soltanto dopo conferma esplicita.

Il motore accettato è sufficiente per la consegna: **non riaprire tuning,
minimax, ISMCTS o nuove ricerche strategiche**. Conserva il simulatore virtuale
giocabile e non cambiare il sito pubblico come effetto dell'integrazione.
Implementa, verifica, correggi e verifica di nuovo. Non fermarti a un piano o
a una demo con tessere simulate spacciate per letture della camera.

Non hai bisogno di credenziali di un'AI esterna per far funzionare il cervello.
Non chiedere all'utente di imparare Git per completare il lavoro locale.
Chiedi solo informazioni essenziali che non trovi dopo l'ispezione, per esempio
il percorso del progetto se non accessibile o la presenza fisica dell'operatore.

## 2. Recupera e identifica la consegna corretta

Repository: <https://github.com/adster2/Reto07-GameEngine>.

- Tag accettato: `consegna-v1.0`.
- Commit sorgente: `53b349bc82db48d44deeeed7df5d2c760755b787`.
- Branch conservato: `release/consegna-v1`.
- **Branch consigliato per il passaggio: `docs/local-integration-handoff`**;
  contiene la stessa consegna più queste istruzioni e gli esempi verificabili.
- Non usare `main` assumendo che contenga il codice, `gh-pages` come sorgente
  Python o `experiment/strategy-lab` come motore del prodotto.

Se non esiste già una copia, clona in una directory nuova, adiacente al progetto
visivo, senza sovrascriverlo:

```bat
git clone --branch docs/local-integration-handoff --single-branch https://github.com/adster2/Reto07-GameEngine.git Reto07-GameEngine
cd Reto07-GameEngine
git merge-base --is-ancestor 53b349bc82db48d44deeeed7df5d2c760755b787 HEAD
python -m handoff.check_engine
```

I comandi assumono di essere nella directory padre scelta dall'agente. Sostituisci
`python` con il Python effettivo individuato al punto successivo. Non usare
`reset --hard` o checkout distruttivi su copie esistenti con modifiche.
Il controllo di ascendenza deve terminare con exit status 0. Il branch
documentale ha un HEAD successivo: non pretendere che HEAD coincida con il
commit del tag. L'hash dei moduli è in `handoff/approved_manifest.json`;
`handoff.check_engine` lo controlla normalizzando soltanto CRLF → LF.
Il manifest è un confronto di versione, non una firma crittografica del fornitore.

Se Git non è installato puoi usare una copia ZIP di quel branch, verificare il
manifest e registrare la provenienza senza inventare una verifica Git eseguita.
Se usi direttamente il tag, il core è lo stesso ma i file `handoff/` e queste
istruzioni vanno presi dal branch documentale. Registra la modalità effettiva.

Leggi integralmente prima di implementare:

1. `CODEX_GAME_ENGINE_SPEC.md` (regole vincolanti).
2. `GAME_ENGINE_DESIGN.md` e il codice delle API che utilizzi.
3. `VISION_INTEGRATION_CONTRACT.md`.
4. `REPORT_CONSEGNA.md`, `TEST_RESULTS.md`, `WEB_TEST_RESULTS.md`.
5. Le istruzioni locali `AGENTS.md`, README e configurazioni del progetto visivo.

La specifica storica parla di memorizzare la mano reale in `GameState`;
per la partita fisica applica il chiarimento del contratto: mantieni i fatti
conosciuti in un tracker pubblico e costruisci `KnowledgeState` direttamente.
`GameState` richiede anche i segreti e resta l'arbitro del simulatore.

## 3. Ispeziona il PC senza rompere quanto già funziona

Trova la radice reale di `Reto07_Domino`, modifiche non salvate, struttura,
interprete Python, eventuale virtualenv, dipendenze, entry point, framework GUI,
flusso camera, calibrazione, ROI, modelli e formato dei riconoscimenti.
Verifica quali output esistono davvero: valori delle facce, bounding box,
orientamento, confidenza, ID temporali e contatti. Non inventare nomi di moduli
locali o assumere che il riconoscitore esponga già una `ObservedScene`.

Prepara un branch locale o una copia di sicurezza reversibile; conserva tutte
le modifiche dell'utente, i modelli e la calibrazione. Non riscaricare né
sostituire modelli funzionanti e non aggiornare globalmente Python/OpenCV.
Usa il virtualenv esistente se compatibile con Python >=3.10; se incompatibile,
documenta il motivo e crea un ambiente separato senza distruggere quello attuale.

Il core ha zero dipendenze pip a runtime. Tkinter serve alla GUI desktop
standalone; se la GUI visiva è già Qt, Tk o altro, integra nel suo framework
senza avviare due event loop concorrenti. Non introdurre `cv2` dentro
`domino_engine`. Puoi installare il core con l'interprete locale:

```bat
python -m pip install --no-deps -e PERCORSO_REALE_DEL_GAME_ENGINE
```

`PERCORSO_REALE_DEL_GAME_ENGINE` è un segnaposto da sostituire e quotare se
contiene spazi. L'installazione editable può scaricare setuptools 84.0.0 per
il build isolato. Per lavorare senza rete puoi includere il package sorgente
accettato nel progetto e verificarne gli hash. Evita import risolti casualmente
da un'altra copia: registra `domino_engine.__file__` e mantieni una sola fonte.
Non basta modificare `sys.path` in modo che funzioni soltanto dalla tua shell.

## 4. Architettura concreta da ottenere

```text
camera / registrazioni esistenti
  → pipeline OpenCV esistente
  → adattatore di stabilità e topologia
  → osservazione / proposta (ancora nessun cambio di stato)
  → interfaccia: Conferma / Correggi / Rileggi / Scarta / Manuale
  → tracker fisico: commit atomico dei soli fatti conosciuti
  → KnowledgeState immutabile
  → StrategyEngine, in worker
  → lista mosse e suggerimento alla persona
```

**Da implementare localmente:** un tracker della partita fisica, per esempio
`integration/physical_session.py`, e un adattatore della pipeline reale.
Il nome è indicativo: non esiste già una classe `PhysicalSession` nel motore.
`handoff.check_engine` non è un tracker né un adattatore camera.

`EventSession(initial: GameState)` è già implementato, ma pretende entrambe le
mani e i 14 esclusi dell'arbitro virtuale. Non usarlo in produzione fisica con
una mano avversaria casuale, vuota o inferita. Una mano vuota significa vittoria,
non «sconosciuta». Non far diventare un'ipotesi del motore uno stato reale.

Mantieni separati i due modi:

- **Virtuale:** `GameState`, `EventSession`, distribuzione e CPU avversaria.
- **Fisico:** mano propria confermata, tavolo, conteggio e avversario umano;
  niente distribuzione casuale e niente mossa automatica della CPU avversaria.

## 5. API del motore accettato

Import reali:

```python
from domino_engine import Tile, OrientedTile, Move, Side, Player
from domino_engine.state import PublicEvent
from domino_engine.rules import moves_for, place
from domino_engine.knowledge import KnowledgeState
from domino_engine.strategy import StrategyEngine, SearchConfig
from domino_engine.events import ObservedTile, ObservedScene, MoveProposal
```

- `Tile(a, b)`: identità canonica, facce intere 0..6, indipendente dalla rotazione.
- `OrientedTile(left, right)`: orientamento nella catena **logica**, non sullo
  schermo. `.tile` restituisce l'identità canonica.
- `Move(tile, Side.LEFT/RIGHT, orientation)`: posa. `Move()` è passaggio.
- `moves_for(hand, chain, terminal=False)`: genera le mosse; se manca una posa
  restituisce `(Move(),)`. Sul tavolo vuoto usa solo RIGHT per evitare duplicati.
- `place(chain, move)`: costruisce la nuova catena; **non verifica la legalità**.
- `PublicEvent(player, move, ends_before)`: storico pubblico. Conservare gli
  estremi prima dell'evento è essenziale per le deduzioni dai passaggi.

Il tracker costruisce questa vista solo da dati confermati e coerenti:

```python
view = KnowledgeState(
    observer=Player.ASSISTED,
    hand=tuple(confirmed_own_hand),
    chain=tuple(confirmed_chain),
    turn=confirmed_turn,
    opponent_count=confirmed_opponent_count,
    history=tuple(public_history),
    passes=consecutive_passes,
    terminal=False,
    winner=None,
    reason=None,
)
ranking = StrategyEngine(SearchConfig(
    level=3, samples=8, max_nodes=6000,
    time_limit_ms=1500.0, seed=20261019,
)).rank(view)
```

I nomi `confirmed_*` sono variabili da implementare nel tracker. Questo esempio
vale durante una partita in corso; non azzerare gli indicatori di una partita
finita per continuare a chiamare il motore.

`ranking.moves` contiene `RankedMove(move, score, heuristic_score, explanation)`;
`ranking.recommendation` è una `Move` oppure `None`. Mostra anche
`ranking.diagnostics`: profondità richiesta/completata, nodi, campioni, tempo e
limite. I punteggi non sono probabilità di vittoria.
Il livello predefinito rimane 3; consenti la scelta 1–5. Il livello 2 ha ottenuto
i migliori risultati del campione storico, senza garantire vittorie umane.

Non passare `GameState`, replay privati, seed del deal, riferimenti all'arbitro
o immagini di mani nascoste al decisore. `knowledge_for(state, player)` serve
alla simulazione; nel fisico non devi creare un arbitro per ottenere la vista.
`KnowledgeState` valida alcuni vincoli, non sostituisce la validazione completa
del tracker. Se la diagnostica dice `inconsistent_knowledge`, blocca l'uso del
suggerimento e chiedi la revisione dei dati, non nascondere il fallback.

## 6. Inizializzazione della partita fisica

1. Separa la scansione della mano dalla scansione del tavolo, tramite modalità
   e ROI adeguate alla pipeline reale.
2. Raccogli sette identità distinte 0..6 in un buffer, mostrandole all'utente.
   Permetti correzione manuale e rilettura; registra solo alla conferma.
3. Memorizza quelle sette tessere e consenti di ritirarle dall'inquadratura.
   La loro scomparsa non è una serie di mosse né una perdita di stato.
4. Inizializza tavolo vuoto, conteggio avversario 7, storico vuoto e zero passaggi.
   Fai indicare/confermare chi inizia in base al sorteggio fisico; non obbligare
   ad aprire col doppio più alto.
5. A ogni nostra posa confermata rimuovi solo la tessera corrispondente dalla
   mano memorizzata. Una posa avversaria confermata riduce solo il suo conteggio.

Per correggere una mano iniziale già usata, applica un processo esplicito di
replay/revalidazione o riavvio; non sostituirla silenziosamente a partita in corso.

## 7. Adattatore OpenCV e geometria

L'adattatore produce `ObservedScene(tiles=tuple(...), geometry_ambiguous=...,
image_ref=...)`. Ogni elemento è
`ObservedTile(a, b, side=Side.RIGHT, orientation=None, confidence=1.0)`.
L'immagine è un riferimento locale opzionale, non un array video nel dominio.

`tiles` rappresenta **l'intera catena sul tavolo**, non soltanto il pezzo nuovo
e non la mano. La baseline è sempre l'ultimo tavolo **confermato**, mai l'ultimo
frame. Confronta le identità canoniche, non coordinate che cambiano quando
si sposta una tessera. Accetta una sola nuova identità, nessuna duplicata e
nessun pezzo confermato mancante. Non cancellare pezzi dal tracker per occlusione.
Zero pezzi nuovi non significa passaggio; più pezzi nuovi richiedono correzione.

Per il nuovo pezzo risolvi lato e orientamento tramite i contatti della catena.
LEFT/RIGHT sono le estremità logiche: una curva può portare LEFT a destra nello
schermo. Le doppie trasversali non aprono diramazioni. Conserva coordinate e
geometria nel livello visivo/presentazione, separati dal dominio lineare.
Se l'associazione o il lato sono ambigui, segnala ambiguità e non indovinare.

Usa stabilità temporale e confidenza reali; la soglia del contratto è 0,8 inclusa
per il nuovo pezzo, con valori ammessi fino a 1. Non inventare confidenza 1,0
se il riconoscitore non la produce: documenta e collauda un criterio di qualità
oppure richiedi conferma/correzione manuale esplicitamente marcata come tale.
La soglia non prova che l'accuratezza sia 80% o calibrata.

Con proposta pendente i frame continuano solo come anteprima. Non generare altre
proposte né aggiornare la baseline; usa il nuovo frame su richiesta di Rileggi.
Una rilettura non valida deve invalidare anche la vecchia proposta confermabile.

## 8. Tracker fisico: validazione e commit

Mantieni almeno: mano iniziale/propria corrente, catena ordinata, turno,
conteggio avversario, `PublicEvent` con `ends_before`, passaggi consecutivi,
proposta pendente, revisione, ID/sessione, eventi confermati e fase del risultato.
Non memorizzare una presunta mano avversaria come verità.

Valida prima della proposta e di nuovo prima del commit:

- Turno atteso, partita aperta, unicità delle identità, continuità della catena,
  limiti del conteggio e coerenza con la mano iniziale/storico.
- Nostra posa: appartenenza esatta a `moves_for(own_hand, chain)`.
- Posa avversaria: tessera non nella mano propria né già giocata, conteggio >0,
  e appartenenza a `moves_for((observed_tile,), chain)` per controllare contatto,
  lato e orientamento. La proprietà effettiva della tessera resta non verificabile
  dalla camera del tavolo; non affermare il contrario.
- Nostro passaggio: solo se `moves_for` restituisce esclusivamente il passaggio.
  Passaggio avversario: azione separata con attestazione umana esplicita.
  Non dedurlo dal tempo trascorso o dall'assenza di una lettura.
- Ogni passaggio conserva gli estremi presenti **in quel momento**. Nella
  variante senza pesca, un successivo pezzo avversario contenente un valore
  prima escluso da un suo passaggio contraddice lo storico: ferma la conferma
  e offri correzione/replay, senza eliminare il vincolo silenziosamente.
- Controlla anche che restino abbastanza tessere avversarie compatibili con i
  fatti pubblici per il conteggio indicato.

Il commit esplicito dell'ID deve essere atomico e idempotente, anche in presenza
di callback concorrenti: un doppio clic non deve applicare due turni. Nessuna
osservazione, suggerimento o selezione cambia la mano prima del commit.
Un ID annullato o appartenente a vecchia sessione/revisione non è riutilizzabile.
Riprendi il comportamento Conferma/Correggi/Rileggi/Scarta/Manuale di
`EventSession`, ma applicalo ai fatti pubblici senza copiarne l'arbitro privato.

Undo ricostruisce dai dati iniziali e dagli eventi pubblici confermati: mano,
conteggio, catena, turno e inferenze devono tornare coerenti insieme.
Definisci un formato versionato di persistenza **fisica**, diverso dal journal
virtuale contenente mani e scarti. Rifiuta salvataggi corrotti e ripristina
tramite replay, non fidandoti del solo snapshot finale.

Dopo undo/caricamento il tavolo reale può non coincidere con quello ripristinato:
metti l'acquisizione in pausa e chiedi di riallineare e confermare il tavolo
prima di riprendere. Altrimenti un pezzo appena annullato verrebbe riproposto
automaticamente dal frame successivo. Non eliminare questo controllo per
semplificare i test.

## 9. Terminalità senza inventare informazioni nascoste

- Mano propria vuota: vittoria ASSISTED verificabile.
- Conteggio avversario zero dopo una posa confermata: vittoria OPPONENT.
- Due passaggi consecutivi: blocco. Il punteggio proprio è noto, quello
  avversario no. Introduci una fase applicativa `awaiting_opponent_score`
  (nome indicativo), disabilita nuove mosse e richiedi conteggio/rivelazione
  avversaria confermata dall'operatore. Poi assegna minor somma o pareggio.

Non assegnare un vincitore stimando la mano avversaria. Non usare
`terminal=True, winner=None` in una `KnowledgeState` per significare «risultato
ignoto»: nel motore `None` terminale significa pareggio. Mentre il risultato è
pendente, non chiamare il decisore e non presentare una vista falsa come attiva.
Registra come evento pubblico anche la conferma dei punti e la sua provenienza;
se vengono rivelate tessere, controlla numero, unicità, somma e compatibilità
con lo storico. Se si immette solo la somma, esplicita che è attestata dall'umano.

## 10. Interfaccia e concorrenza

Riusa la GUI locale e il riconoscitore attuali. Mostra camera/overlay, mano
confermata, catena ed estremi, turno, conteggio avversario e stato della proposta.
Per la proposta mostra facce, lato, orientamento, nuovi estremi, qualità/ambiguità,
fonte manuale/visiva ed errore se illegale. La conferma è abilitata solo su
proposta valida. Offri sempre correzione, rilettura, scarto, inserimento manuale,
passaggio esplicito e undo; i fallimenti della camera devono essere recuperabili.

Calcola il ranking in un worker usando uno snapshot immutabile. Le callback GUI
devono controllare sessione, revisione, livello e generazione della richiesta.
Un risultato avviato prima di un commit, undo, nuova partita, caricamento o
cambio livello non deve sovrascrivere la vista nuova. Non bloccare video o UI
durante ricerca e non aggiornare widget da thread non autorizzati dal framework.

Il consiglio non esegue una posa: attendi il pezzo reale e la conferma. Nel modo
fisico disattiva i percorsi della GUI virtuale che inventano la mano avversaria,
distribuiscono nuove tessere o fanno giocare automaticamente la CPU.

## 11. Verifiche locali obbligatorie

Prima di cambiare codice esegui e registra la baseline:

```bat
python -m handoff.check_engine
python -m unittest discover -v
python virtual_game.py --seed 42 --level 3
```

La suite accettata ha 48 test. In ambiente privo di display tre test Tk vengono
saltati; riporta PASS e SKIP separatamente e verifica i widget sul vero Windows.
Non fare fallire la baseline perché eseguita dalla directory errata. I comandi
vanno dalla radice del Game Engine con l'interprete scelto. Registra versioni,
exit status e modulo importato. Dopo l'integrazione ripeti le regressioni toccate.

Aggiungi test significativi per il nuovo adattatore/tracker:

- Scansione mano confermata, ritiro dalla camera e aggiornamenti solo al commit.
- Lettura 3–5 invece di 3–6, correzione, lato/orientamento sbagliati, doppie e
  curve; zero/multiple aggiunte, duplicati, occlusione e confidenza insufficiente.
- Proposta pendente, rilettura fallita, turno errato, passaggio proprio illegale,
  passaggio avversario attestato e successive contraddizioni.
- Doppio commit anche concorrente, ID obsoleti, undo/replay, caricamento corrotto,
  riallineamento del tavolo e risultati asincroni ormai superati.
- Vittoria per mano vuota, blocco con risultato ancora ignoto, punti avversari
  confermati e pareggio. Nessuna assegnazione anticipata di esiti stimati.
- Privacy: a stessa `KnowledgeState`, varia la verità nascosta nel solo harness
  di test e verifica che il ranking resti identico con stesso budget/seed.

Esegui inoltre **almeno 1.000 partite deterministiche attraverso il nuovo tracker
fisico**, usando proiezioni pubbliche delle partite generate dall'arbitro
virtuale come sorgente controllata di osservazioni. La verità delle mani resta
solo nel test harness. Non usare l'arbitro o mani inventate nel codice fisico.
Confronta dopo ogni commit mano nostra, catena, turno, conteggio, passaggi e
storico con la proiezione dell'arbitro; al blocco fornisci i punti tramite la
stessa conferma prevista per l'operatore. Verifica replay e invarianti, salva
seed, quantità, semimosse ed eventuali violazioni. Un solo confronto dello stato
finale non basta. Queste sono prove **nuove dell'integrazione**, non le 6.000
partite cloud già eseguite, e non misurano l'accuratezza di OpenCV.

Usa poi registrazioni/camera locali con verità annotata per quantificare almeno
letture corrette, rifiutate e false proposte prima della conferma, specificando
numero di tessere/eventi, condizioni e denominatori. Scegli soglie verificabili
in base ai dati reali; non inventare un'accuratezza o cambiare le etichette per
far passare il test. Distingui robustezza del protocollo da qualità ottica.

Completa almeno una **partita fisica dall'inizio alla fine** con camera e
operatore, includendo scansione mano, consigli e conferme. Registra cosa è
stato realmente provato e gli interventi manuali necessari. Se camera/operatore
non sono disponibili, concludi le prove indipendenti e marca questa prova
`NOT_RUN`, indicando la precisa azione ancora necessaria; non dichiarare il
prodotto fisico collaudato.

## 12. Consegna finale richiesta all'agente locale

Lascia nel progetto locale:

1. L'app unita funzionante, con modalità fisica e simulatore ancora disponibili.
2. Adattatore e tracker separati dal core accettato; se emerge un difetto del
   core, riproducilo con un test e documenta ogni modifica necessaria invece
   di sostituire la strategia. Conserva il riferimento originale e i nuovi hash.
3. Un launcher Windows concreto per l'ambiente reale, con percorsi corretti,
   e istruzioni semplici di avvio, scansione mano, conferma e recupero errori.
4. Test e log riproducibili con seed, versioni, sorgente importata, risultati e
   numero di prove PASS/FAIL/SKIP/NOT_RUN. Nessun test non eseguito come PASS.
5. `INTEGRAZIONE_LOCALE_REPORT.md` con file cambiati, decisioni, prove, tempi
   effettivi sul PC, accuratezza visiva misurata, limitazioni e passi residui.
6. Una dimostrazione o log della partita reale, se eseguita, e indicazione
   esplicita dei casi che hanno richiesto correzione umana.

Il core deve restare importabile e testabile senza camera. Non richiedere una
telecamera per avviare il simulatore. Non confondere salvataggi privati virtuali
con dati della partita fisica e non esporre mani nascoste al cervello.

Procedi fino a completare il lavoro concretamente eseguibile sul PC. Se un
limite reale impedisce una parte, documenta esattamente il limite e ciò che
manca; non usare una schermata funzionante come prova di integrazione completa.
