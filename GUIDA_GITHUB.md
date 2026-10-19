# La nostra guida semplice a GitHub

GitHub è il posto dove conserviamo il progetto e la sua storia. Per giocare online
basta aprire il link del gioco: non serve conoscere Git, scaricare il codice o
installare Python.

## I tre posti da distinguere

| Posto | A cosa serve |
|---|---|
| Il gioco online | Apri la pagina, scegli il livello e giochi contro la CPU. Il link è nel README. |
| [Il progetto su GitHub](https://github.com/adster2/Reto07-GameEngine) | Contiene tutti i file: cervello, interfacce, test, istruzioni e risultati. |
| L'ambiente cloud di questa chat | È la macchina sulla quale sviluppo e provo il programma per te. |

Il pulsante **Pubblica** dell'ambiente cloud conserva quella macchina preparata.
La pubblicazione del **gioco online** è invece gestita da GitHub Pages. Sono due
operazioni diverse: per giocare usi soltanto il link del gioco.

## Dove trovo i file?

Apri il progetto su GitHub e scegli la scheda **Code**. L'elenco al centro contiene
file e cartelle. Clicca un nome per leggerne il contenuto; il README viene mostrato
anche sotto l'elenco.

Oggi il lavoro nuovo si trova nella versione chiamata
**`feat/domino-engine-simulator`**. Puoi aprirla direttamente qui:

[Apri tutti i file del progetto sviluppato](https://github.com/adster2/Reto07-GameEngine/tree/feat/domino-engine-simulator).

In alto a sinistra dell'elenco c'è un selettore che normalmente mostra **main**.
Quel selettore cambia la versione che stai guardando. Se vedi soltanto pochi file,
controlla quale versione è selezionata: i file non sono spariti.

| Nome | Significato semplice |
|---|---|
| Repository | L'intero progetto, comprese le versioni precedenti. |
| main | La versione principale del progetto. |
| Branch | Una versione di lavoro separata, nella quale prepariamo gli aggiornamenti. |
| Commit | Un salvataggio identificabile della storia del progetto. |
| Pull request, abbreviata PR | La proposta di inserire un aggiornamento nella versione principale. |
| gh-pages | La copia generata che GitHub usa per mostrare il sito del gioco. |

## La pull request: cosa devo fare?

La nostra proposta è [PR #1](https://github.com/adster2/Reto07-GameEngine/pull/1).
Aprendola trovi la descrizione del lavoro e, nella scheda **Files changed**, i file
aggiunti o modificati. Io posso continuare ad aggiornarla mentre lavoriamo.

Se vuoi rendere quel lavoro parte della versione principale:

1. Apri la PR #1 e leggi la descrizione.
2. Se GitHub mostra il pulsante verde **Merge pull request**, premilo.
3. Conferma con **Confirm merge**.
4. Tornando in **Code**, scegli **main**: troverai anche lì il progetto aggiornato.

Questa operazione approva l'aggiornamento della versione principale. Non è
necessaria per giocare al sito già pubblicato. Non l'ho eseguita automaticamente:
la PR resta disponibile per la tua revisione.

## Dove sono il cervello, il gioco e le prove?

| File o cartella | Cosa ci trovi |
|---|---|
| `README.md` | Pagina iniziale, link del gioco e istruzioni. |
| `domino_engine/strategy.py` | Il cervello strategico della CPU. |
| `domino_engine/rules.py` | Le regole delle mosse legali. |
| `domino_engine/state.py` | Lo stato della partita e la contabilità delle tessere. |
| `domino_engine/knowledge.py` | Le informazioni che l'AI può conoscere, senza vedere la mano avversaria. |
| `web/` | La pagina con cui giochi dal browser. |
| `virtual_game.py` e `run_simulator.cmd` | La versione desktop, se in futuro vuoi usarla sul PC. |
| `tests/` | Le prove automatiche del programma. |
| `TEST_RESULTS.md` | I risultati del motore e dei tornei già eseguiti. |
| `WEB_TEST_RESULTS.md` | Le prove specifiche della nuova versione browser. |
| `PROJECT_STATUS.md` | Cosa è completo e cosa resta da verificare. |
| `VISION_INTEGRATION_CONTRACT.md` | Come collegare in futuro la telecamera del tuo progetto locale. |

Per consultare questi file basta cliccarli. Se desideri una modifica, descrivila
qui in chat: posso prepararla, provarla e caricarla nella proposta di aggiornamento.
Per questa collaborazione non devi imparare comandi da terminale.

## Se compare la parola “conflitto”

**“Ambiente modificato” nella schermata cloud:** riguarda due versioni delle
impostazioni della macchina di lavoro. Se non hai aggiunto impostazioni tue,
“Annulla le modifiche non salvate” ricarica quelle salvate più di recente; il
codice su GitHub resta conservato. Se hai scritto impostazioni personali,
conservale prima di scartarle.

**Conflitto in una pull request GitHub:** due aggiornamenti hanno cambiato gli
stessi punti di un file. In quel caso mandami il messaggio: posso confrontare le
versioni e risolverlo preservando il lavoro. Non significa che il progetto sia perso.

## Come giochiamo online?

Apri il link indicato nel README, attendi il primo caricamento, clicca una tua
tessera disponibile e scegli una posa. Prima di confermare, usa le frecce
**Destra / Basso / Sinistra / Alto** per far proseguire o curvare la catena.
La tessera evidenziata sul tavolo è un'anteprima: puoi cambiare direzione senza
consumare il turno. Le frecce non disponibili non lasciano spazio; le doppie si
posano di traverso. S e D indicano le due estremità sulle quali puoi giocare.
Premi **Conferma mossa**. La CPU pensa,
propone la propria tessera e aspetta che tu confermi anche quella. Il livello si
sceglie dal selettore CPU o quando inizi una nuova partita. I consigli per te sono
facoltativi e inizialmente nascosti.

Serve un browser moderno e la connessione per caricare la pagina e il motore.
Le partite vengono calcolate nel browser: non occorrono account o installazioni.
Il primo caricamento è più lungo dei successivi. Puoi salvare una partita da
**Salva o riprendi una partita**; ricaricare la pagina senza salvarla ne inizia
una nuova. Sul telefono la mano scorre orizzontalmente e il tavolo si adatta
allo schermo. Il salvataggio conserva anche la disposizione delle tessere;
le vecchie partite salvate si aprono con una disposizione automatica.
