# Risultati della versione browser — 19 ottobre 2026

## Aggiornamento: curve e direzione della posa

Sorgente collaudata: `825ad490bd00c55559ffc65fcc17fd6aa1efb418`.
La modifica riguarda la presentazione del tavolo, senza cambiare regole o AI.

| Verifica mirata | Risultato |
|---|---|
| Geometria JavaScript | **PASS**, 8 controlli: doppie trasversali, curve su entrambi gli estremi, collisioni, catena da 14 tessere, replay, passaggi, immutabilità e metadati non validi |
| Regressione bridge Python | **PASS**, 8/8 test, zero skip |
| Partita reale Chromium | **PASS**, seed 42, livello 3, 13 eventi confermati, CPU originale |
| Direzioni e anteprima | **PASS**, quattro direzioni esercitate, 48 controlli geometrici, nessun cambiamento di token/vista/proposta scegliendo una direzione |
| Recupero e annullamento | **PASS**, save/load conserva la disposizione; undo, scarto, vecchi salvataggi e nuova partita verificati |
| Viewport 375×812 | **PASS**, tavolo ridimensionato senza sovrapposizioni, tessere tagliate o overflow della pagina |
| Errori JavaScript | **PASS**, zero errori osservati |
| Nuovi tornei del motore | **NOT_RUN**, non necessari per questa modifica del renderer |
| Verifica HTTPS dell'aggiornamento pubblico | **BLOCKED**, il proxy cloud continua a restituire CONNECT 403 |

Comandi eseguiti: `node scripts/test_table_layout.cjs`,
`python -m unittest tests.test_web_bridge -v`, `python scripts/build_web.py`,
`python scripts/test_table_browser.py --environment-tls`.
Il runner usa una partita vera e i pulsanti dell'interfaccia; le prove geometriche
isolate usano anche una catena pubblica controllata di 14 tessere distinte.
Nessuna verifica TLS viene disattivata. Il telefono fisico resta **NOT_RUN**.

[Report, hash sorgenti, log e schermate](docs/web-results/table-placement/VALIDATION.json).
Il proprietario ha attivato Pages e confermato una partita nel sito originale;
la verifica indipendente dell'aggiornamento dal cloud rimane distinta da questa
conferma. Il report seguente conserva i risultati storici della prima consegna.

## Consegna browser iniziale

Codice sorgente: `7e073848c4182ff64fe76e8dc89bc157ecee83eb` sul branch
`feat/domino-engine-simulator`. Il codice aggiunge un bridge JSON e una pagina
web; le regole e l'algoritmo strategico già collaudati non sono duplicati o riscritti.
Le nuove prove sono concluse; dopo la richiesta dell'utente non sono avviate
ulteriori campagne. Le attività residue riguardano soltanto l'attivazione del sito.

| Verifica | Risultato osservato |
|---|---|
| Suite completa Python con display Linux | **PASS**, 48/48 test, zero errori, zero fallimenti, zero skip |
| Partite complete Chromium | **PASS**, 5 partite ai livelli 1–5 e una partita su viewport mobile |
| Widget browser | **PASS**, scelta tessera/lato, conferma umana e CPU, passaggi, consigli, nuova partita |
| Recupero partita | **PASS**, salvataggio, caricamento, scarto e undo tramite i controlli reali |
| Mobile 375×812 | **PASS**, partita completa e assenza di overflow della pagina |
| Privacy del bridge | **PASS**, vista del giocatore filtrata; alla CPU arriva soltanto KnowledgeState |
| Token e idempotenza | **PASS**, doppio commit innocuo e richieste di vecchie partite respinte |
| Distribuzione Python | **PASS**, moduli copiati byte per byte e SHA-256 verificato dal worker |
| 1.000 partite via protocollo JSON | **PASS**, seed 40000–40999, 12.966 semimosse, zero violazioni, 1.000 replay |
| Caricamento statico su GitHub | **PASS**, sito completo salvato nel branch `gh-pages` |
| Attivazione GitHub Pages | **NON CONFERMATA**, API bloccata dal proxy cloud con 403 |
| Verifica del sito pubblico | **BLOCKED**, stesso blocco di rete; nessun indirizzo è dichiarato raggiungibile |
| Browser su telefono fisico / Safari / Firefox | **NOT_RUN**, la prova mobile è un'emulazione Chromium |

## Prove eseguite

```
DISPLAY=:99 python -m unittest discover -v
python scripts/build_web.py
python scripts/test_web_browser.py --environment-tls
python scripts/stress_web.py --games 1000
python scripts/publish_web.py --publish
python scripts/publish_web.py --branch-only
```

Il primo tentativo di pubblicazione completa si è fermato sull'accesso all'API,
prima di cambiare la configurazione Pages. Il secondo comando ha preparato e
caricato il branch statico senza modificare la sorgente dell'ambiente o main.
Commit del sito: `b75430becebe67e3e5d887328be0e300b38ef1f0`.
[Metadati del caricamento](docs/web-results/PAGES_DEPLOYMENT.json).
`pages_configured: false` indica che lo script non ha potuto confermare o attivare
Pages; non è una lettura autorevole delle impostazioni attuali del proprietario.

Le sei partite Chromium sono state concluse attraverso i pulsanti reali, usando
la CPU AI e un giocatore umano automatizzato con sole mosse legali visibili.
Cinque usano seed 42 e livelli 1–5, con 13 eventi ciascuna. La prova mobile usa
anche seed 43 per consigli, save/load, scarto e undo, poi una partita completa
seed 42, livello 2. Nessun errore JavaScript rilevato. Nessun test ha sostituito il
motore con una simulazione finta o una risposta mock.

Le 42 decisioni CPU osservate nel browser hanno p95 circa **186,8 ms**, massimo
**568,6 ms**, zero budget esauriti. Questo è un piccolo controllo funzionale sui
seed dichiarati, non un nuovo benchmark indipendente della forza o una garanzia
per ogni telefono. Restano validi separatamente i tornei e i benchmark CPython
in TEST_RESULTS.md; i numeri non vengono mescolati.

Chromium nel container non possiede la CA del proxy HTTPS. La prima prova di
caricamento diretto ha mostrato `ERR_CERT_AUTHORITY_INVALID`. La prova completata
usa il trasporto HTTPS verificato di urllib con la CA dell'ambiente e inoltra le
risposte al browser. Non vengono disabilitati controlli TLS o ignorati errori di
certificato. Le pagine locali sono state usate esclusivamente per il collaudo
interno, non sono un indirizzo pubblico o una preview per l'utente.

## Per rendere disponibile il gioco

Il proprietario può aprire
[GitHub → Settings → Pages](https://github.com/adster2/Reto07-GameEngine/settings/pages),
scegliere **Deploy from a branch**, branch **gh-pages**, cartella **/ (root)** e
premere **Save**. Quando GitHub mostra **Visit site**, il gioco è accessibile
all'indirizzo indicato lì. L'indirizzo previsto è
`https://adster2.github.io/Reto07-GameEngine/`, ma non è stato possibile verificarlo
da questa macchina. Se GitHub segnala una limitazione del piano o dei permessi,
serve quella specifica azione del proprietario; non viene cambiata la visibilità
del repository e non vengono richieste chiavi in chat.

Dati e schermate: [docs/web-results](docs/web-results/).
Guida per principianti: [GUIDA_GITHUB.md](GUIDA_GITHUB.md).
