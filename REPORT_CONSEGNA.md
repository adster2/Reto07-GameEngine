# RETO 07 — Report di consegna e passaggio al PC locale

Data: 19 ottobre 2026. Decisione del proprietario: usare il motore già accettato
e fermare gli esperimenti strategici. Questo documento descrive il lavoro cloud;
non dichiara eseguita l'integrazione con i file OpenCV del PC.

## 1. Quale versione usare

| Riferimento | Uso |
|---|---|
| Tag `consegna-v1.0` | Versione accettata e congelata |
| Commit `53b349bc82db48d44deeeed7df5d2c760755b787` | Sorgenti della consegna, inclusi desktop e browser con curve |
| Branch `release/consegna-v1` | Copia della consegna conservata separatamente |
| Branch `docs/local-integration-handoff` | Stessi sorgenti accettati, più questo report, istruzioni locali e controllo eseguibile |
| Branch `experiment/strategy-lab` | Ricerca archiviata, esclusa dall'integrazione finale |
| Branch `gh-pages` | Sito statico, non sorgente da usare per integrare Python |

Per iniziare sul PC usare **`docs/local-integration-handoff`**: contiene il motore
accettato e il materiale di passaggio. Il suo HEAD ha un commit documentale
successivo a quello della consegna; il codice `domino_engine` resta quello
approvato, verificabile con `python -m handoff.check_engine`.
Il branch `main` può ancora contenere la sola specifica: non assumerlo aggiornato.

Il gioco online resta disponibile a:
<https://adster2.github.io/Reto07-GameEngine/>.
La sua pubblicazione usa `gh-pages`, commit
`0192cb9654acfa381835f70c457e35dadffeb088`. Il proprietario ha confermato di averci
giocato. La verifica HTTPS indipendente dal cloud è stata bloccata dal proxy.
La consegna originaria ha la [pull request #1](https://github.com/adster2/Reto07-GameEngine/pull/1);
un branch caricato non equivale a una PR unita in `main`.

## 2. Che cosa è stato realizzato

- **Dominio e regole:** identità delle tessere, orientamento, mosse legali,
  transizioni immutabili, turni, passaggi, vittoria, blocco, pareggio e validazione.
- **Cervello strategico:** vista informativa separata dall'arbitro, esclusione delle
  tessere note, vincoli ricavati dai passaggi, euristica e ricerca su mani
  avversarie ipotetiche compatibili; cinque profondità, budget e diagnostica.
- **Simulatore:** distribuzioni riproducibili, avversari casuale/greedy/AI,
  CLI, scenari JSON, tornei, benchmark, salvataggi, replay e audit delle partite.
- **Gioco desktop:** GUI Tk realmente collegata al motore, umano contro CPU,
  scelta livello, mano, tavolo, mosse ordinate, suggerimenti facoltativi,
  conferma/correzione/rilettura/scarto/inserimento manuale, undo e salvataggi.
- **Gioco browser:** lo stesso motore Python eseguito con Pyodide in un worker,
  CPU ai cinque livelli, interfaccia responsive, mosse confermate, curve della
  catena e doppie trasversali, salvataggio/caricamento della disposizione.
- **Contratto visione:** osservazioni separate dagli eventi confermati,
  riconoscimento di un solo pezzo nuovo rispetto al tavolo confermato, gestione
  degli errori e nessuna dipendenza OpenCV dentro il motore.

Il cervello non è un servizio generativo: non richiede chiavi API o connessione
Internet nel programma Python locale. Legge la situazione conosciuta e ordina
tutte le mosse legali. I punteggi sono utilità, non percentuali di vittoria.

## 3. Regole effettivamente implementate

Domino doppio-sei: 28 tessere uniche, due giocatori, sette tessere ciascuno,
14 escluse definitivamente e **nessuna pesca**. Nel simulatore il primo giocatore
è sorteggiato; può aprire con qualunque tessera. Si posa un pezzo per turno su
una delle due estremità con valore compatibile. Curve e doppie trasversali non
creano rami: la catena logica rimane lineare.

Si passa soltanto senza pose legali. Mano vuota: vittoria immediata. Due passaggi
consecutivi: blocco; vince chi conserva meno punti, oppure pareggio a parità.
Una sola manche. Non confondere queste regole con varianti con pesca,
apertura obbligatoria o punteggio cumulativo.

## 4. Come decide l'AI accettata

`StrategyEngine.rank(KnowledgeState)` riceve solo mano propria, catena, turno,
conteggio avversario, passaggi e storico pubblico. Non riceve la vera mano
avversaria, i 14 esclusi o il seed della distribuzione.

Il motore considera punti residui, mobilità, varietà dei valori, rischio dei
doppi rimasti e probabilità di blocco. Per le ricerche oltre la prima semimossa
campiona mani avversarie plausibili senza sostituzione e simula risposte con una
policy greedy. I livelli 1–5 limitano a 1–5 **semimosse individuali**, passaggi
inclusi; non sono cinque algoritmi diversi né una promessa di forza crescente.

Configurazione accettata: livello predefinito 3, otto campioni, 6.000 nodi,
1.500 ms, seed di ricerca 20261019. L'euristica usa pesi iniziali documentati;
non è stata svolta un'ottimizzazione automatica dei pesi. La strategia è
approssimata e può perdere anche contro un principiante. Le 14 tessere escluse
impediscono di ricostruire con certezza la mano avversaria dal solo conteggio.

## 5. Verifiche quantitative già eseguite

Questa è una sintesi di campagne storiche documentate, non l'affermazione di
averle rieseguite tutte durante la preparazione del passaggio al PC.

| Verifica | Esito e quantità |
|---|---|
| Suite Python della versione browser | **48/48 PASS**, zero fallimenti/errori/skip, con display Linux |
| Stress del dominio | **1.000 partite**, 13.126 semimosse, zero violazioni e replay verificati |
| Torneo indipendente | **4.000 partite**, 52.662 semimosse, zero violazioni e replay verificati |
| Stress del bridge JSON browser | **1.000 partite**, 12.966 semimosse, zero violazioni e replay verificati |
| Totale delle tre campagne sopra | **6.000 partite, 78.754 semimosse**, zero violazioni rilevate |
| Separazione informazioni | Test anticheat: stessi ranking a conoscenza identica cambiando realmente i segreti, livelli 1–5 |
| Desktop Tk Linux | Cinque partite complete tramite GUI reale, una per livello |
| Browser Chromium | Sei partite complete, livelli 1–5 e viewport mobile 375×812 |
| Aggiornamento curve browser | Otto controlli JS, otto regressioni bridge, una partita reale aggiuntiva, 48 controlli geometrici, zero errori pagina |
| Benchmark CPython livello 5 | 150 posizioni; media 55,86 ms, p95 186,00 ms, massimo 257,09 ms; tutte a profondità 5, zero cutoff |

I 6.000 incontri non includono le 1.000 partite di sviluppo né gli esperimenti
del laboratorio. Lo stress del bridge esercita il protocollo Python JSON;
non significa 1.000 partite azionate in Chromium. Le prove effettive in Chromium
sono quelle indicate separatamente. Il benchmark è su Linux/Python 3.12.14,
AMD EPYC, cinque CPU disponibili; non garantisce gli stessi tempi sul PC Windows.

### Forza strategica misurata

Punti partita = vittoria 1, pareggio 0,5, sconfitta 0. Ogni cella usa 400 partite
su 100 distribuzioni indipendenti, con posti e primo giocatore bilanciati.

| Livello | Punti contro casuale | Punti contro greedy |
|---|---:|---:|
| 1 | 64,500% | 53,375% |
| 2 | 67,500% | 59,500% |
| 3 | 61,125% | 56,625% |
| 4 | 66,250% | 57,625% |
| 5 | 60,125% | 55,375% |

Il livello 2 è risultato il migliore nel campione. Il suo IC95% per deal è
63,67–71,33% contro casuale e 55,23–63,77% contro greedy. Tutti gli altri
intervalli, W/D/L, seed e limiti sono in [TEST_RESULTS.md](TEST_RESULTS.md).
Non si garantisce una vittoria contro l'utente o il professore.

Evidenze complete:
[TEST_RESULTS.md](TEST_RESULTS.md), [WEB_TEST_RESULTS.md](WEB_TEST_RESULTS.md),
[docs/results](docs/results/), [docs/web-results](docs/web-results/).
La verifica dei nuovi esempi del passaggio è registrata separatamente in
[handoff/VERIFICATION.json](handoff/VERIFICATION.json).
Durante questo passaggio: 15 moduli del core verificati contro il manifest,
ranking con sole informazioni note e protocollo virtuale **PASS**. Suite
rieseguita senza display: **45 test PASS, tre SKIP Tk**, zero errori/fallimenti;
il precedente 48/48 con display resta un risultato storico distinto.

## 6. Esito del progetto parallelo

La ricerca è conservata in `experiment/strategy-lab`: modello della mano,
minimax sperimentale e successivo ISMCTS con fattori tattici. Le 1.344 partite
indipendenti del laboratorio non hanno dimostrato un miglioramento contro il
motore accettato: 49,11% dei punti contro il vecchio livello 2 e 52,23% contro
il livello 3; entrambi gli IC95% comprendono il 50%.

Per decisione del proprietario **non viene promossa nel prodotto finale**.
Il motore accettato e il sito sono stati preservati. I 70 test del laboratorio
non vanno riportati come suite della consegna, che ne ha 48.
[Risultati e dati della ricerca](https://github.com/adster2/Reto07-GameEngine/blob/experiment/strategy-lab/docs/strategy-lab/RESULTS.md).

## 7. Cosa manca per unire il progetto alla telecamera

La pipeline OpenCV locale non è stata letta, modificata o collaudata dal cloud.
Il motore può già ragionare senza conoscere la mano avversaria, ma il gestore
`EventSession` esistente usa un arbitro virtuale che conosce entrambe le mani.
Non basta collegarlo alla camera fingendo una mano avversaria.

L'agente locale dovrà realizzare **un gestore della partita fisica con sole
informazioni conosciute**, adattare le letture della pipeline esistente e
collegare la GUI. Il dettaglio operativo è in
[ISTRUZIONI_AGENTE_LOCALE.md](ISTRUZIONI_AGENTE_LOCALE.md).
Nel prodotto fisico l'AI suggerisce al giocatore assistito; l'avversario è umano.

Il lavoro locale comprende registrazione e conferma delle sette tessere proprie,
catena e turni, osservazione → proposta → conferma, correzioni e replay,
ricerca asincrona e prove con camera. Un passaggio avversario richiede conferma
umana; al blocco servono i punti residui avversari per assegnare il risultato.
La camera del tavolo non può verificare ciò che è nascosto.

**NOT_RUN sul PC:** installazione nell'ambiente reale, launcher Windows,
resa grafica/DPI, camera e modelli, accuratezza del riconoscimento, tracker fisico,
partita fisica completa. Anche Firefox, Safari e telefono fisico restano non
collaudati. La viewport mobile cloud era un'emulazione Chromium.

## 8. Avvio e verifica del materiale ricevuto

Dalla radice della copia `docs/local-integration-handoff`, con Python 3.10+:

```bat
python -m handoff.check_engine
python -m unittest discover -v
python virtual_game.py --seed 42 --level 3
```

Usare l'interprete effettivo del progetto OpenCV, ad esempio il suo
`.venv\Scripts\python.exe`, se presente. Tkinter serve soltanto al desktop.
Il motore non richiede pacchetti pip. L'installazione editable è facoltativa
(`python -m pip install --no-deps -e .`) e può scaricare il backend setuptools
84.0.0; l'esecuzione diretta dalla radice non lo richiede.

`handoff.check_engine` controlla gli hash del core rispetto alla consegna e
verifica due esempi: ranking da sole informazioni note e protocollo
osservazione/conferma su **fixture virtuale**. Non implementa il tracker fisico
e non certifica la camera. Su checkout Windows normalizza CRLF a LF per gli hash.

L'agente locale dovrà consegnare un comando o launcher concreto per l'app unita,
un report con esiti PASS/FAIL/SKIP/NOT_RUN e almeno una partita fisica verificata
quando camera e operatore saranno disponibili. Fino a quel collaudo, la
consegna cloud è il motore con simulatore e contratto d'integrazione.
