# Contratto del futuro adattatore OpenCV

Questa consegna non legge video né file del progetto locale `Reto07_Domino`.
L'adattatore futuro resta esterno a `domino_engine`: trasforma riconoscimenti e
geometria in **osservazioni**, mai in modifiche dirette di mani o catena.
L'esempio seguente è eseguibile con l'arbitro virtuale per collaudare il protocollo;
non rappresenta un'integrazione fisica già eseguita.

## Input

```python
from domino_engine import deal, Side, OrientedTile
from domino_engine.events import EventSession, ObservedScene, ObservedTile

session = EventSession(deal(42))
scene = ObservedScene(
    tiles=(ObservedTile(3, 6, Side.RIGHT, OrientedTile(3, 6), confidence=0.95),),
    geometry_ambiguous=False,
    image_ref=None,  # opzionale: percorso locale PNG/GIF; non pixel nel dominio
)
proposal = session.observe(scene)
```

`tiles` è una **tupla dell'intera catena sul tavolo**, non la mano iniziale né un
elenco dei soli pezzi nuovi. `a,b` sono facce 0..6, identità canonica a prescindere
da orientamento e ordine. `side` e `orientation` della sola tessera nuova devono
essere risolti dall'adattatore. L'orientamento è sempre sinistra→destra nella
catena topologica, anche se la tessera appare ruotata, trasversale o in una curva
nell'immagine. Le doppie hanno due facce uguali e nessun ramo.

L'adattatore deve mantenere l'associazione topologica di tessere e contatti,
e segnalare `geometry_ambiguous=True` quando non può stabilire il lato o il
collegamento. Gli spostamenti dei pezzi confermati non sono nuove pose. Il core
confronta le identità con la baseline confermata, non le coordinate e non la
precedente scena grezza. Confidenza <0.8 della nuova tessera, identità duplicate,
pezzi mancanti, zero o più pezzi nuovi non producono una proposta confermabile.
La soglia non pretende di essere una probabilità calibrata del riconoscitore.

## Output e conferma

`MoveProposal` (alias `ProposedMove`) contiene `id`, revisione, giocatore previsto,
`Move`, legalità, motivo del rifiuto, nuovi estremi, fonte e immagine opzionale.
`None` significa osservazione non sufficiente: leggere `last_observation_error`
e chiedere correzione/acquisizione. Lo stato autorevole e la mano non cambiano.

La GUI mostra tessera, lato, orientamento, estremi, legalità e, se fornita,
anteprima PNG/GIF. Il riconoscitore non deve chiamare `commit` automaticamente.
La pressione esplicita di Conferma chiama `session.commit(proposal.id)`.
Una tessera sbagliata [3|5] può essere corretta con:

```python
from domino_engine import Move, Tile
fixed = Move(Tile(3, 6), Side.RIGHT, OrientedTile(3, 6))
proposal = session.correct(proposal.id, fixed)
# Mostrare nuovamente la proposta. Confermare solo se proposal.legal.
```

`reread(id, new_scene)` confronta la nuova acquisizione con la catena confermata;
`discard(id)` abbandona la proposta; `undo()` ricostruisce tramite replay e quindi
ripristina anche la baseline. Il passaggio è `session.propose(Move())`, su
controllo separato, ed esige conferma. In simulazione è verificabile contro la
mano vera dell'arbitro, mai usando la mano vera nel decisore.

## Registrazione della mano e partita fisica

La GUI virtuale offre deal 7+7 e registrazione manuale confermata di sette tessere.
Per la futura registrazione visiva: raccogliere sette identità distinte in un
buffer dell'adattatore, visualizzarle all'utente, salvarle **solo dopo conferma**,
poi ignorare le immagini di quella mano e aggiornarla solo al commit delle pose
ASSISTED. Non trattare la scomparsa della mano dalla scena come sette mosse.

Il simulatore usa `GameState` con entrambe le mani per fare l'arbitro. Nella
partita fisica la mano OPPONENT e i 14 esclusi sono ignoti: **non inventarli e non
passare una determinizzazione come se fosse lo stato reale**. Il tracker pubblico
fisico dovrà mantenere mano propria, catena, conteggio, turno e PublicEvent con
`ends_before`; può costruire direttamente una `KnowledgeState` immutabile e
chiamare `StrategyEngine.rank`. Non occorre conoscere i pezzi fuori gioco.
La futura persistenza e il commit di questo tracker fisico sono un'attività
d'integrazione separata dall'arbitro virtuale implementato qui. Le primitive
`moves_for` e `place` sono riutilizzabili senza duplicare le regole di contatto.

La presenza della tessera nella mano propria è verificabile. La proprietà di una
tessera avversaria, la veridicità del suo passaggio e il suo totale in un blocco
non possono essere provati dalla sola camera del tavolo: servirà una conferma
umana e, al blocco, il conteggio/rivelazione dei punti residui. La futura UI deve
esplicitare queste informazioni non verificabili; la simulazione invece le
verifica completamente tramite l'arbitro. Nessun risultato fisico è dichiarato
collaudato da questa consegna.

## Confine dell'AI

Passare solo `knowledge_for(state, player)` in simulazione, o una KnowledgeState
costruita dal tracker pubblico in futuro. Mai `GameState`, replay privati, buffer
video con mani nascoste, callback all'arbitro o RNG del deal. I test anticheat
controllano tutti i livelli cambiando realmente mano e scarti avversari a vista
identica. I test del protocollo coprono errore [3|5]/[3|6], lato sbagliato,
rilettura, ambiguità, passaggio illegale, doppio commit e undo.
