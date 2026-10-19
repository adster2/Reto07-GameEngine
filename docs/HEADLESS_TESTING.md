# Collaudo Tk senza schermo fisico

Sul container Debian 13 usato in questa sessione sono già installati Xorg e il
driver dummy. Non è stato installato un server web, né pubblicato un URL locale.
Questi comandi sono stati eseguiti realmente dalla directory del repository:

```sh
Xorg :99 -config "$PWD/docs/testing-xorg.conf" -logfile /tmp/reto07-xorg.log -nolisten tcp -noreset -novtswitch
```

Il primo comando resta in esecuzione; in un secondo terminale:

```sh
DISPLAY=:99 python -m unittest discover -v
DISPLAY=:99 python virtual_game.py --smoke --level 5 --seed 42
```

Il file di configurazione copia quello effettivamente usato. Il display è
accessibile solo nel container; non è una preview remota utilizzabile dal browser
dell'utente. Se mancano Xorg/driver usare un display desktop o Xvfb installato dal
sistema, oppure `python virtual_game.py --headless-smoke`, che verifica solo il
controller e non i widget. Le tre prove `test_tk_gui` vengono saltate senza display;
nel collaudo finale di questa sessione hanno invece girato tutte, senza skip.

Il server X e le finestre sono processi, non vengono considerati persistenti nel
filesystem della configurazione cloud. Il programma non richiede un servizio
permanente: sul PC Windows si avvia direttamente con `run_simulator.cmd`.

[Schermata effettiva Linux](gui-linux.png): la catena visualizzata è uno stato
reale del motore, con consigli nascosti, mano cliccabile e CPU AI di livello 5.
