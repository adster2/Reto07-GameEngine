# Versione browser e pubblicazione

Il sito è statico: HTML/CSS/JavaScript più gli stessi moduli Python del desktop,
eseguiti con Pyodide 0.27.7 in un Dedicated Web Worker. Nessun backend, account
utente, chiave API, database o servizio a pagamento richiesto dal gioco.
GitHub Pages serve i file; jsDelivr serve il runtime Python via HTTPS. Il primo
avvio scarica circa 14 MB di runtime. Il browser può riusare la propria cache.
La versione desktop resta eseguibile offline, come prima.

## Disposizione del tavolo nel browser

`web/table-layout.js` dispone la catena pubblica in due dimensioni. Ogni tessera
conserva l'ordine logico delle facce fornito da Python: le curve cambiano solo
coordinate e rotazione, le doppie sono trasversali. Le frecce nella proposta
permettono di scegliere la direzione prima del commit, con anteprima evidenziata.
Le collisioni e le direzioni che allungano inutilmente il tavolo sono escluse
quando esiste una posa compatta. Una disposizione manuale che circonda un'estremità
viene riordinata per lasciare giocabile la mossa legale; questa scelta grafica
non crea passaggi, nuove estremità o cambiamenti nelle regole.

La CPU usa la disposizione automatica; anche la sua proposta può essere ruotata
prima di confermarla. Undo ricostruisce la disposizione dalla cronologia pubblica.
Il campo opzionale `table_layout` nei salvataggi contiene solo identità pubbliche
e direzioni grafiche; i vecchi file restano caricabili. Il motore e il contratto
della camera non ricevono coordinate del tavolo virtuale.

Regressioni mirate, senza ripetere i tornei del motore:

```sh
node scripts/test_table_layout.cjs
python -m unittest tests.test_web_bridge -v
python scripts/test_table_browser.py --environment-tls
```

Node e Playwright sono strumenti di sviluppo opzionali. Non servono a chi gioca.
Il runner browser richiede un server statico interno della directory generata;
URL e directory risultati sono configurabili con `--url` e `--output`.

## Un solo motore

`python scripts/build_web.py` genera `local_runs/site/`. Copia byte per byte
nove moduli dal pacchetto `domino_engine`, compresa la nuova API `WebGame`.
Il manifest contiene SHA-256 di ogni modulo: il worker li verifica prima di
importarli. Non esiste una seconda implementazione JavaScript delle regole o
dell'AI. JavaScript visualizza esclusivamente la KnowledgeState del giocatore,
le mosse legali e le proposte pubbliche. Il worker mantiene l'arbitro privato.

`WebGame.handle_json` accetta comandi dichiarati, un token versione della partita
e mosse nel formato del dominio. Conferme ripetute sono idempotenti; token di
vecchie partite vengono rifiutati anche quando gli ID locali delle mosse coincidono.
Correzione/rilettura e commit passano attraverso EventSession. I salvataggi privati
sono scaricati solo su richiesta; non vengono inviati a un server. I token
proteggono la coerenza, non sono autenticazione per un servizio remoto.

Entrambi i bot fair e i consigli usano KnowledgeState, mai lo stato dell'arbitro.
La CPU usa StrategyEngine e il seed di ricerca indipendente dal deal. In browser
restano 8 campioni, 6.000 nodi e 1.500 ms: eventuali fallback sono dichiarati nella
sezione “Cosa ha calcolato l'AI?”. Il renderer non si blocca durante la ricerca.
Un utente con gli strumenti di sviluppo controlla il proprio processo browser:
non si pretende protezione contro l'ispezione manuale della memoria di una
simulazione client-side; la separazione informativa dell'AI è quella verificata
dai test. Non ci sono multiplayer, classifica o risultati certificati remoti.

## Pubblicazione riproducibile

Dopo aver salvato e committato le modifiche:

```sh
python scripts/build_web.py
python scripts/publish_web.py --publish
```

Il publisher legge l'identità dal remote GitHub, controlla la configurazione Pages,
crea un commit contenente solo il sito generato e lo invia a `gh-pages` senza
cambiare checkout, index o sorgenti. Usa fast-forward, mai force push; conserva
un branch preesistente non riconosciuto e una configurazione Pages di altro tipo.
Se il sito non esiste, richiede tramite API l'attivazione della sorgente legacy
`gh-pages`, cartella `/`. Le credenziali sono quelle già fornite dalla piattaforma;
nessuna viene scritta nei file o nello script.

L'API Pages richiede permessi di amministrazione Pages sul repository. Se questo
accesso non è disponibile, `--branch-only` prepara comunque il ramo pubblicabile;
il proprietario può poi aprire GitHub → Settings → Pages → Deploy from a branch,
scegliere `gh-pages`, `/ (root)` e Save. Una pubblicazione effettiva viene dichiarata
solo dopo il build GitHub e una verifica HTTPS dell'indirizzo restituito da Pages.
L'indirizzo previsto per questo repository è
`https://adster2.github.io/Reto07-GameEngine/`; lo stato realmente verificato è in
WEB_TEST_RESULTS.md e nel README.

Non modificare direttamente i file generati di `gh-pages`: gli aggiornamenti si
fanno nel codice sorgente e si ripubblicano. Unire la PR a main non modifica da
solo il sito: serve un nuovo build/publish quando cambia il codice web o il motore.

## Verifica per lo sviluppo

La suite Python rimane `python -m unittest discover -v`. Comprende test autonomi
del bridge, dei token, della privacy, di partite complete ai livelli 1–5 e della
corrispondenza binaria tra moduli originali e moduli distribuiti.

Per le prove browser serve il pacchetto di sviluppo opzionale `playwright` e
Chromium. Servire internamente la directory generata, poi eseguire:

```sh
python scripts/test_web_browser.py --url <indirizzo-del-sito-da-testare>
```

Il runner gioca sei partite reali con pulsanti e dialoghi, una su viewport mobile;
verifica ricerca CPU, passaggi, conferme, mano filtrata, assenza di duplicati
visibili, consigli, save/load, scarto, undo, nuova partita e overflow mobile.
Le misure browser non vanno confuse con i vecchi benchmark CPython.

Nel container, Chromium non riconosce direttamente la CA del proxy HTTPS.
L'opzione di test `--environment-tls` inoltra le richieste HTTPS attraverso urllib
con la CA fidata dell'ambiente e verifica TLS attiva, poi passa le risposte al
browser. Non usa ignore_https_errors né disabilita controlli dei certificati.
Questo adattamento serve al collaudo della macchina cloud; gli utenti aprono
normalmente il sito HTTPS nel proprio browser. La guida al progetto destinata
all'utente è GUIDA_GITHUB.md, senza queste procedure tecniche.
