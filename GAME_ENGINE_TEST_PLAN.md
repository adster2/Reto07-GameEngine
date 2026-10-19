# Piano di collaudo e criteri

I risultati effettivamente eseguiti sono in TEST_RESULTS.md; questo file descrive
cosa controllano i comandi. Nessun test preesistente è stato modificato o rimosso:
il repository iniziale conteneva solo README e specifica.

| Ambito | Prove | Esito atteso |
|---|---|---|
| Tessere | Canonizzazione, intervalli, tipi, orientamento | 28 identità, nessun duplicato |
| Regole | Apertura libera, doppie, lati uguali/diversi, ribaltamento, turno, mano | Solo mosse compatibili e un pezzo per turno |
| Passaggi | Obbligo quando bloccato, divieto quando giocabile, reset dopo posa | Nessuna pesca o modifica mani durante il passaggio |
| Terminalità | Mano vuota, due passaggi, minore somma, pareggio | Fine immediata e nessuna mossa successiva |
| Transizioni | Partite a seed fissi, immutabilità, contabilità | Conservazione di tutte le 28 tessere |
| Eventi | Proposta/correzione/rilettura/scarto/conferma, input ambiguo | Nessuna mutazione prima del commit |
| Atomicità | Otto commit concorrenti dello stesso ID | Un solo evento e una sola transizione |
| Replay/undo | Salva/carica, replay di partite complete, undo di tutti gli eventi | Stato identico e inferenze ripristinate |
| Privacy | Cambiare veri segreti con stessa vista, seed e budget | Ranking e scelta identici ai livelli 1–5 |
| Inferenza | Passaggi con estremi storici, campioni senza sostituzione | Nessun candidato contrario ai passaggi |
| Ricerca | Profondità 1–5, passaggio come semimossa, fallback di tempo/nodi | Tutte le mosse ordinate, profondità/limiti dichiarati |
| GUI controller | Partite complete ai livelli 1 e 5; risultati async obsoleti | Nessuna desincronizzazione o dato nascosto renderizzato |
| GUI Tk | `--smoke` su display Linux; pulsanti effettivi | Intera partita confermata fino al risultato |
| Scenari | Otto JSON controllati | Catena, stato, proposta, esiti e knowledge attesi |
| Stress | 1.000 partite + 1.000 replay | Zero violazioni, duplicati, passaggi illegali o deadlock |
| Tornei | Deal indipendenti, entrambe posizioni/primi giocatori | W/L/D, punti 1/0.5/0, tempo, nodi e campioni esportati |
| Prestazioni | 150 posizioni indipendenti, livello 5 | p95 decisioni <= 5.000 ms; riportare anche fallback |

Il comando base è `python -m unittest discover -v`; i comandi riproducibili
completi si trovano nel README. Gli scenari falliscono se un'aspettativa differisce;
i runner non nascondono errori e preservano exit status nonzero. Non si accetta
un test con zero casi, una sola porta aperta o una schermata mockup come prova.

Il set di sviluppo (25 deal × 4 repliche per livello/bot) non è usato per dichiarare
il risultato indipendente. La valutazione usa altri 100 deal × 4 repliche per
livello/bot. Le quattro partite dello stesso deal sono correlate: gli intervalli
approssimati usano la media del deal come unità, non 400 Bernoulli indipendenti.
I bot non accedono mai alla mano vera dell'altro, nemmeno nei tornei.
Il target del 60% è riportato come stima osservata con incertezza; nessuna soglia
viene abbassata e nessun seed sfavorevole viene rimosso.

Gate Windows e camera: avvio `.cmd`, resa visiva, input e DPI sul PC Windows;
riconoscimenti fisici, stima geometrica e tracker pubblico reale restano prove
d'integrazione future, esplicitamente separate dai gate della simulazione.
