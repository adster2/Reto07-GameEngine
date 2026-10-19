# Architettura e API

## Confini

`tiles` → `state` / `rules` → `events` → `simulation` / `controller` → `gui`.
`knowledge` proietta lo stato dell'arbitro; `strategy` riceve **solo** quella
proiezione. Il core non importa Tkinter, OpenCV o alcuna API di camera. La GUI
importa Tkinter solo quando viene effettivamente creata una finestra.
L'arbitro virtuale contiene informazioni private necessarie a verificare le mosse;
non vengono passati riferimenti all'arbitro, seed del deal o RNG ai decisori.

## Tipi e invarianti

- `Tile(a,b)`: dataclass frozen, identità canonica `(min,max)`, interi 0..6.
- `OrientedTile(left,right)`: orientamento logico da sinistra a destra, non pixel.
- `Move(tile, side, orientation)`: posa esplicita; `Move()` è un passaggio.
- `Player.ASSISTED` / `Player.OPPONENT`; proprietà `.other` e `.index`.
- `GameState`: mani vere tuple, 14 scarti nei deal standard, catena ordinata,
  turno, passaggi, cronologia pubblica, esito e seed privato di riproduzione.
- `KnowledgeState`: mano propria, catena, turno, conteggio avversario, passaggi,
  cronologia con estremi al momento dell'evento, esito e identificatore regole.
  Nessun campo `hands`, `excluded`, `seed`, RNG o callback sull'arbitro.
- `EventSession`: stato iniziale immutabile, journal confermato, una sola proposta
  pendente, revisione e identificatori monotoni. Lock rientrante su mutazioni e letture.

`validate_state` controlla che ciascuna delle 28 identità occorra esattamente una
volta fra mani/catena/scarti, compatibilità della catena, passaggi ed esito.
`from_hands` permette scenari ridotti e distribuzioni manuali; tessere non elencate
sono escluse, mai pescabili. `deal(seed, first=None)` distribuisce 7+7 e sorteggia
l'iniziante con un RNG locale. L'override `first` serve ai confronti bilanciati.
Una posa modifica una sola mano, una passata nessuna. Nessun punteggio cumulativo.

## API di dominio

```python
from domino_engine import Player, deal, legal_moves, apply_move
from domino_engine.knowledge import knowledge_for
from domino_engine.strategy import StrategyEngine, SearchConfig
from domino_engine.events import EventSession

state = deal(42)
view = knowledge_for(state, state.turn)
ranking = StrategyEngine(SearchConfig(level=5)).rank(view)
session = EventSession(state)
proposal = session.propose(ranking.recommendation)
assert session.state == state                 # nessuna mutazione anticipata
if proposal.legal:
    session.commit(proposal.id)
session.undo()                               # replay, non manipolazione inversa
```

`legal_moves(state, player)` restituisce vuoto se è il turno sbagliato o la partita
è terminale; altrimenti tutte le pose o l'unico passaggio obbligatorio.
`apply_move` restituisce un nuovo stato o solleva `IllegalMove` senza modificare
l'originale. `moves_for(hand, chain)` e `place` sono le primitive condivise: bot,
ricerca, arbitro e GUI non ridefiniscono le regole. Su tavolo vuoto LEFT/RIGHT
sono equivalenti e si emette solo RIGHT; entrambi gli orientamenti non doppi
restano distinti. Su tavolo non vuoto si conservano entrambi i lati quando legali,
anche con estremi uguali. Le doppie non creano rami.

`GameState.to_json/from_json`: snapshot **privato** versione 1.
`EventSession.to_json/from_json`: stato iniziale, eventi confermati, stato finale e
contatore ID. Il caricamento riapplica ogni evento (anche verificando l'attore) e
confronta il finale; non accetta l'esito dichiarato senza replay. Una proposta non
confermata non entra nel salvataggio. Il formato non è una firma crittografica:
chi può riscrivere coerentemente l'intero file può creare un altro scenario valido.

## Eventi e undo

`observe(ObservedScene)` confronta identità con la **baseline confermata** della
catena. Richiede una sola tessera nuova, nessuna tessera confermata mancante,
nessun duplicato, geometria non ambigua e confidenza della nuova tessera >=0.8.
Una proposta illegale può essere ispezionata ma non confermata.
`correct(id, move)` e `reread(id, scene)` rieseguono le verifiche. Una rilettura
ambigua rende non confermabile la proposta precedente. `discard` non muta il gioco.
`commit(id)` ricalcola la transizione sotto lock, poi pubblica stato/evento una
volta sola. Il doppio commit è idempotente; un ID annullato viene rifiutato.
`undo` rigioca gli eventi rimasti dallo stato iniziale: mano, inferenze dei passaggi,
conteggio e terminalità vengono ricostruiti insieme.

## Inferenza senza informazioni segrete

L'insieme invisibile è `ALL_TILES − mano propria − catena`, **inclusi i 14 scarti**.
Se OPPONENT passa, i valori degli estremi in QUEL momento sono esclusi dalla sua
mano corrente: senza pesca ogni tessera ancora in mano era già presente al passo.
Le successive pose pubbliche vengono rimosse dall'insieme invisibile. Non si usa
l'estremità di oggi per reinterpretare un passo precedente.
`sample_world(view, rng)` sceglie senza sostituzione una mano avversaria del
conteggio osservato fra candidati compatibili. Tutto il resto è escluso nel mondo
ipotetico. Distribuzione uniforme condizionata sui passaggi, non modello appreso
delle scelte avversarie. Se non esistono abbastanza candidati si dichiara
`inconsistent_knowledge`, senza inventare una mano plausibile.

## Strategia e pesi

Utilità non terminale (limitata a [-500,500]):

```
  8.0 * (conteggio avversario - conteggio proprio)
+ 1.3 * (punti avversari - punti propri)
+ 2.5 * (mobilità propria - mobilità avversaria)
+ 0.6 * numeri distinti rimasti nella mano propria
- 0.8 * punti delle doppie proprie senza contatto con gli estremi
```

Mobilità = numero di tessere in mano che toccano almeno un estremo.
Vittoria +1000, sconfitta -1000, pareggio 0. Al livello 1 i punti e la mobilità
avversaria sono aspettative analitiche sul pool invisibile condizionato;
si aggiunge `8 * P(avversario senza contatto)` con probabilità ipergeometrica.
Lo scarico dei punti alti è quindi premiato, mentre una doppia alta bloccata
riceve una penalità aggiuntiva. Per un secondo passo terminale si campionano gli
esiti compatibili anziché usare un semplice differenziale di punti.

Livelli 2–5: stessi mondi ipotetici per tutte le mosse candidate (numeri casuali
comuni), ricerca iterativa di 2..livello semimosse. Nei nodi propri si massimizza
l'utilità; nei nodi avversari si applica il bot greedy alla **mano ipotetica**.
Il bot greedy scarica più punti, poi massimizza la mobilità residua. Non legge mai
la mano reale. Si media l'utilità su 8 campioni, con massimo 6.000 transizioni e
1.500 ms per decisione. Le passate consumano esattamente una semimossa.

Un'iterazione aggiorna il ranking solo se ha valutato **tutte** le mosse su tutti
i campioni: nessun vantaggio per le prime mosse quando finisce il budget. Resta
sempre disponibile l'intero ranking dell'ultima iterazione completata (inizialmente
livello 1). Diagnostica: profondità richiesta/completata, semimosse effettivamente
visitate, nodi, mondi campionati, ms, limite incontrato. Un albero concluso prima
per terminalità conta come completato alla profondità limite senza espandere dopo
la fine della partita.

`score` è la stima dopo ricerca, `heuristic_score` la valutazione immediata.
Stessa scala di utilità, nessuna calibrazione come probabilità. Ordinamento stabile
con spareggio canonico. Seed di ricerca indipendente dal deal; nei bot il seed
varia solo con indice pubblico di semimossa e giocatore. Il cutoff di tempo può
variare tra esecuzioni; quello di nodi è riproducibile.

Pesi iniziali verificati sul set di sviluppo 1000–1024. Non sono stati cambiati
in base ai seed indipendenti 10000–10099. Nessuna pretesa di ottimalità o incremento
monotono di forza fra i livelli: determinizzazione, campioni finiti, policy greedy
e *strategy fusion* nelle continuazioni proprie sono approssimazioni esplicite.
Non è minimax sulla mano vera e non risolve esattamente il gioco bayesiano.

## GUI e concorrenza

`GameController` invia solo una KnowledgeState al worker singolo. Tk viene toccato
solo dal thread principale, tramite polling `after`. Il risultato è scartato se
sessione, revisione, livello o generazione sono cambiati mentre cercava. La CPU usa per default lo stesso StrategyEngine al livello scelto; i bot di
baseline restano disponibili soltanto tramite l'opzione esplicita `--opponent`.
La mano permette selezione diretta con scelta di lato/orientamento e i suggerimenti
sono inizialmente nascosti per consentire una sfida umana. Non esistono conferme
implicite delle mosse nella GUI normale. `--smoke` aziona invece
i pulsanti in modo automatico per il collaudo. La vista renderizzata è quella
ASSISTED; i salvataggi restano artefatti privati dell'arbitro.
