# Stato del progetto

Il repository ora contiene un gioco Python reale, eseguibile offline. Il giocatore
umano può sfidare una CPU alimentata dal nostro StrategyEngine ai livelli 1–5;
la mano è cliccabile, la CPU propone le proprie pose automaticamente, i consigli
all'umano sono facoltativi e inizialmente nascosti. Confermare le pose è parte
del protocollo universale richiesto, anche per la CPU. Non sono necessari OpenCV,
video, credenziali, server web o pacchetti pip per l'avvio dal sorgente.

## Completato

1. Packaging e dominio: 28 tessere canoniche, orientamenti logici, catena lineare,
   regole no-draw, terminalità, stati immutabili, setup manuale e seed.
2. CLI, scenari JSON, proposte, correzioni, riletture, scarto, commit atomico e
   idempotente, undo e salvataggio/replay rigoroso.
3. KnowledgeState filtrata, vincoli dei passaggi storici, campioni plausibili senza
   sostituzione, bot fair e test anticheat su tutti i livelli.
4. Euristica esplicita, ranking completo, motivazioni, utilità distinta da probabilità.
5. Ricerca 1–5 semimosse, budget di nodi/tempo, fallback completo e diagnostica.
6. GUI Tkinter collegata al core: mano, scelte di lato/orientamento, CPU AI,
   difficoltà, consigli facoltativi, catena, conferme, storico, undo, replay,
   registrazione della mano, anteprima PNG/GIF e ricerca asincrona.
7. 1.000 partite stress e 4.000 incontri indipendenti, tutti riprodotti senza
   violazioni; benchmark 150 posizioni; 40 test e partite Tk ai cinque livelli.
8. README, architettura/API, contratto camera, piano test, risultati quantitativi,
   log e trascrizioni. Configurazione cloud di installazione/avvio salvata in bozza.

I numeri e i gate PASS/NOT_RUN sono in [TEST_RESULTS.md](TEST_RESULTS.md).
Nessun test preesistente è stato rimosso o indebolito: prima esistevano solo README
e specifica. Nessun file locale della pipeline OpenCV è stato letto o modificato.

## Per giocare sul PC

Usare Python 3.10+ con Tkinter, aprire la directory di questo repository e avviare
`run_simulator.cmd` oppure `py -3 virtual_game.py --level 5`. Scegliere il livello
CPU, cliccare una tessera e una posa legale, quindi Conferma. Al turno CPU
attendere la proposta e confermarla. Nuova partita permette di variare il seed.
Le tessere disabilitate non sono giocabili; il passaggio è obbligatorio solo
quando nessuna posa è possibile. Nessuna pesca o registrazione di account.

La GUI Linux è stata avviata davvero, ispezionata e collaudata con cinque partite
complete. Il launcher `.cmd`, la resa, il DPI e gli input Windows sono **NOT_RUN**
in questo ambiente: richiedono un primo collaudo sul PC. L'installazione del
pacchetto è stata verificata in un virtualenv separato fuori dal checkout.

## Limiti conosciuti e attività successive

- La ricerca è una determinizzazione campionata con policy avversaria greedy e
  strategy fusion nelle continuazioni proprie; non è una soluzione ottimale.
  La forza non è monotona nella profondità. Risultati completi, compresi i
  confronti sfavorevoli e l'incertezza statistica, sono nel report.
- I pesi iniziali non hanno avuto un'ottimizzazione automatica. Eventuale tuning
  futuro deve usare nuovi seed di sviluppo e una nuova valutazione indipendente.
- Nessuna integrazione fisica completata: il futuro tracker pubblico deve
  registrare la mano confermata e gestire conteggio avversario, passaggi attestati
  e punti rivelati a un blocco senza inventare la mano nascosta. Contratto in
  VISION_INTEGRATION_CONTRACT.md; l'arbitro virtuale e l'AI sono già separati.
- Le prove non dimostrano correttezza su ogni possibile stato né prestazioni su
  ogni PC. Il budget temporale è dichiarato e può causare fallback su macchine lente.

## Configurazione cloud e pubblicazione GitHub

Salvati nella bozza: `install_script`, `start_skill` e aggiunta di `api.github.com`
alla lista personalizzata di rete, preservando i preset esistenti. Lo script è
stato eseguito e ripetuto nella macchina corrente; il salvataggio non pubblica
la configurazione né prova il ripristino di una nuova macchina.

Push completato sul branch `feat/domino-engine-simulator` e pull request aperta:
[PR #1](https://github.com/adster2/Reto07-GameEngine/pull/1), verso `main`.
L'API aveva inizialmente restituito 403; il tentativo finale è riuscito con
l'autenticazione già presente, senza richiedere altre chiavi. Non c'è un blocco
GitHub residuo. Comando e risposta effettivi sono in
`docs/results/GITHUB_DELIVERY.json` e nei log associati.

La configurazione cloud rimane una bozza salvata: rivedere e salvare le modifiche
nelle impostazioni, quindi **pubblicare l'ambiente** per renderla riutilizzabile
secondo il flusso del prodotto. Non viene dichiarata una pubblicazione né un
ripristino in un nuovo task: questi passaggi non sono stati eseguiti dall'agente.
