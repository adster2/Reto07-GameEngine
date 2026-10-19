# Risultati della versione browser — 19 ottobre 2026

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
