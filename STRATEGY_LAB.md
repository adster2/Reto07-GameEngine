# Laboratorio strategico separato

La consegna accettata è congelata a `53b349bc82db48d44deeeed7df5d2c760755b787`:

- tag [consegna-v1.0](https://github.com/adster2/Reto07-GameEngine/tree/consegna-v1.0);
- ramo [release/consegna-v1](https://github.com/adster2/Reto07-GameEngine/tree/release/consegna-v1);
- sito corrente generato su `gh-pages`, commit `0192cb9654acfa381835f70c457e35dadffeb088`.

Il ramo `experiment/strategy-lab` aggiunge il laboratorio `strategy_lab/` e
prove/documenti propri. Non modifica i file della consegna, il motore originale,
l'interfaccia browser o `gh-pages`. Non pubblicare il laboratorio sul sito della
consegna prima di una valutazione indipendente. I risultati reali sono in
[docs/strategy-lab/RESULTS.md](docs/strategy-lab/RESULTS.md): il primo esperimento
non dimostra ancora un vantaggio sulla CPU accettata.
Il metodo principale è ora ISMCTS; minimax rimane solo un confronto documentato.

## Il ragionamento sulle tessere è corretto, con un limite importante

La CPU conosce le proprie sette tessere e quelle pubbliche. All'inizio restano
21 identità sconosciute: sette sono dell'avversario e 14 sono fuori gioco.
Senza altre informazioni, ogni tessera sconosciuta ha probabilità 7/21 di essere
nella mano avversaria. Le possibili mani sono C(21,7) = 116.280.

Quando l'avversario posa una tessera, questa viene eliminata dai candidati e il
conteggio della sua mano diminuisce. Le nostre pose spostano tessere già note
dalla mano al tavolo: non eliminano un'altra tessera sconosciuta. Dopo sei pose
avversarie, se non ci sono altre informazioni, rimangono 15 identità compatibili
con la sua ultima tessera, non una sola. Le 14 escluse restano sconosciute.

Un passaggio obbligatorio è una prova più forte: esclude dalla mano corrente
ogni tessera contenente i valori liberi in quel momento. Non essendoci pesca,
questa esclusione resta valida. Si usano gli estremi storici del passaggio.
Giocare sull'altro estremo non prova invece che manchi un certo valore: le
scelte volontarie non vengono convertite in esclusioni certe.
Il conteggio di base era già presente nella consegna; il laboratorio ne espone
le probabilità marginali, le tessere certamente escluse, il numero combinatorio
delle mani e la probabilità che l'avversario debba passare.

Il modello è uniforme condizionato a tessere viste e passaggi. Non è ancora un
modello delle preferenze nelle scelte volontarie dell'avversario. Le probabilità
sono quelle di questo modello, non certezze sulla mano vera.

## Confronto iniziale: minimax e funzione euristica

Minimax cerca la mossa migliore per noi assumendo che l'avversario scelga la
risposta peggiore per noi. Alpha-beta evita rami che non possono cambiare il
risultato. È una scelta standard per giochi avversariali a informazione completa.
Qui le mani sono nascoste: il laboratorio campiona **32 mani ipotetiche distinte**,
compatibili con le informazioni pubbliche, e valuta ogni nostra mossa sulle
stesse mani. Se tutte le mani compatibili sono al massimo 32, le enumera tutte.

In ogni mondo ipotetico applica minimax con alpha-beta e cache delle trasposizioni
con limiti inferiori/superiori corretti. Fa la media dei punteggi; un parametro
di rischio opzionale sottrae un multiplo della deviazione standard, senza
spacciarlo per una probabilità di vittoria. Configurazione iniziale: rischio 0.

Rispetto alla consegna, l'avversario simulato può scegliere qualsiasi risposta
legale: non è vincolato alla policy greedy. La valutazione simmetrica comprende
conteggio tessere, punti residui, mosse disponibili, raggiungibilità dei numeri
tramite le tessere della mano, collegamenti, pezzi isolati, doppie irraggiungibili
e turno. Riconosce anche chiusure e blocchi inevitabili nei mondi ipotetici.
I pesi sono iniziali e documentati in `strategy_lab/heuristic.py`; **non sono
stati addestrati o ottimizzati**. Definire una funzione più ricca non dimostra
automaticamente che sia più forte.

Livelli 1–5 = massimo 1–5 semimosse individuali, passaggi compresi. Ricerca
iterativa: il ranking cambia solo dopo un'iterazione completa per tutte le mosse
e tutte le mani. Budget iniziali 18.000 transizioni / 1.500 ms. Se si interrompe,
rimane l'ultimo ranking completo; profondità 0 indica il fallback euristico
pubblico prima che si completi la prima iterazione. Nodi, profondità, campioni,
tempo, cache e potature sono rendicontati.

### Limite che resta aperto

Il metodo è una determinizzazione: media minimax di mondi separati. Nelle
continuazioni può ancora scegliere varianti diverse per mani segrete che nella
partita reale non saprebbe distinguere (*strategy fusion*). Anche l'avversario
ipotetico viene modellato come perfettamente informato nel suo mondo. Enumerare
tutte le mani elimina l'errore di campionamento, non queste approssimazioni.
Non è una soluzione dell'equilibrio bayesiano. Un successivo esperimento potrà
confrontarlo con ricerca su insiemi informativi o CFR, mantenendo questo come
baseline misurabile. Non legge mai la mano vera del simulatore.

## Metodo principale dopo la revisione: ISMCTS

Il minimax sopra è conservato come confronto. Il metodo principale è
**Single-Observer Information Set Monte Carlo Tree Search**, in
`strategy_lab/ismcts.py`. Le decisioni dell'albero sono condivise per la stessa
storia pubblica tra mani ipotetiche diverse. Non si sceglie una nostra continuazione
ottima separata per ogni mano segreta, come avviene nella determinizzazione minimax.
I conteggi di disponibilità gestiscono le diverse mosse legali dell'avversario.

Ogni simulazione sceglie una mano compatibile da un pool di massimo 128 mani
distinte e gioca una partita completa mediante le regole originali. Le policy
delle continuazioni ricevono soltanto la KnowledgeState del giocatore simulato,
mai la mano segreta dell'altro. Si alternano mosse tattiche e una piccola quota
di mosse casuali. UCT bilancia esplorazione e sfruttamento dei risultati.

Configurazione iniziale: 256 simulazioni richieste, massimo 30.000 transizioni
e 1.500 ms; una sola simulazione quando la mossa è obbligata. Una simulazione
interrotta non riceve ricompensa. Se non si coprono tutte le mosse iniziali si
restituisce l'intero ranking tattico pubblico. La scelta principale è il figlio
più visitato: **lo score ISMCTS è il numero di visite**, non utilità minimax né
probabilità di vittoria. Le spiegazioni distinguono visite, punti medi simulati
e punteggio euristico iniziale.

I livelli 1–5 del laboratorio ISMCTS limitano la profondità dell'albero esplicito;
le simulazioni che lo valutano continuano fino alla fine della partita, entro
44 semimosse. Questa è una semantica sperimentale diversa da quella della
consegna e del controllo minimax. La diagnostica espone entrambe: profondità
dell'albero, limite delle simulazioni, transizioni e simulazioni completate.
La versione consegnata conserva i suoi cinque limiti di 1–5 semimosse.

SO-ISMCTS è un'approssimazione: dipende da policy di rollout, budget e modello
dell'avversario. La condivisione dell'albero riduce il problema delle decisioni
separate per mondo, ma non dimostra un equilibrio bayesiano o elimina ogni bias
da determinizzazione. Le preferenze nelle pose volontarie non sono ancora un
modello probabilistico appreso. Le percentuali delle mani restano condizionate
soltanto alle informazioni pubbliche certe.

### Strategie umane tradotte in codice

`strategy_lab/tactics.py` valuta ogni mossa dalla sola vista del giocatore:

| Principio | Fattore calcolato |
|---|---|
| Doppi pesanti | Bonus per scaricare punti e doppie, bilanciato dai fattori di controllo |
| Diversificazione | Numero di valori residui, mobilità e tessere raggiungibili |
| Debolezze dai passaggi | Esclusioni certe e probabilità ipergeometrica di un nuovo passo |
| Tessere ponte | Penalità per le altre tessere che perdono accesso agli estremi |
| Seme forte | Frequenza dei nostri valori lasciati alle estremità |
| Estremità uguali / monopolio | Probabilità che l'avversario non tocchi nessun estremo, con il rischio del nostro stesso blocco |
| Chiusura ai punti | Conteggio esatto delle somme delle mani compatibili tramite programmazione dinamica, quando la nostra mano residua non può muovere |

La probabilità di blocco include le 14 tessere escluse. La valutazione ai punti
confronta i punti residui, non il numero di tessere. Non si converte una regola
pratica in un obbligo assoluto. I pesi sono iniziali, pubblicati in TacticalWeights;
le policy di rollout usano una stima più economica dei punti per rispettare il
budget, mentre la priorità iniziale usa il conteggio esatto nel modello uniforme.

## Avvio dalla cartella del repository

Python 3.10+, nessuna dipendenza pip del laboratorio:

```sh
python -m strategy_lab inspect --seed 42
python -m strategy_lab rank --seed 42 --level 3 --samples 128 --iterations 256
python -m strategy_lab rank --algorithm minimax --seed 42 --level 3 --samples 32
python -m strategy_lab inspect --replay partita.json --player OPPONENT
python -m strategy_lab.gui --seed 42 --level 3
```

`inspect` mostra la stima dal punto di vista selezionato, predefinito il giocatore
di turno. Accetta journal EventSession e salvataggi del sito originale. Questi
file contengono l'arbitro privato, ma solo KnowledgeState entra nell'AI.
La GUI desktop del laboratorio riusa i widget originali, offre conferma, undo,
livelli e consigli con la nuova CPU. È separata dal gioco browser già consegnato.
Non richiede la camera o i file del PC; su Windows servono Python e Tkinter.

Confronto riproducibile, stessi deal e quattro combinazioni di posto/iniziante:

```sh
python -m strategy_lab arena --deals 20 --seed-start 70000 --workers 4 --output local_runs/lab-development
python -m strategy_lab arena --deals 84 --seed-start 80000 --opponents ai2 ai3 greedy random --workers 4 --output local_runs/lab-holdout
python -m unittest tests.test_strategy_lab tests.test_strategy_lab_mcts -v
python -m strategy_lab.audit local_runs/lab-holdout
```

Un confronto da 84 deal × 4 combinazioni × 4 avversari comprende 1.344 partite.
Le baseline sono il cervello consegnato ai livelli 2 e 3, greedy e random, tutti fair.
Ogni partita passa per EventSession, con validazione a ogni commit e replay finale.
CSV, diagnostiche e journal completi compressi permettono di verificare gli esiti.
Gli intervalli sono calcolati sulle medie dei deal, non fingendo indipendenza
fra le quattro partite della stessa distribuzione. Sono confronti esplorativi.

I seed di sviluppo 70000–70019 e gli smoke 71000–71001 sono separati dalla
valutazione 80000–80083 e dai
vecchi tornei. I risultati reali, compresi quelli negativi, vanno riportati prima
di scegliere un aggiornamento. I tempi CPython non provano le prestazioni Pyodide.
Il sito della consegna viene aggiornato soltanto con una decisione successiva.
