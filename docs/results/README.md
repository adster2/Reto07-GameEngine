# Evidenza del collaudo

- `VALIDATION_RUN.json`: commit e hash del codice, comandi, exit status e log.
- `STRESS_RESULTS.csv`: 1.000 partite, seed 20000–20999; riepilogo nel log stress.
- `TOURNAMENT_RESULTS.csv`: 4.000 incontri, seed 10000–10099, posizioni/primi giocatori bilanciati.
- `TOURNAMENT_DECISIONS.csv`: 26.451 decisioni e relativa diagnostica.
- `TOURNAMENT_EVENTS.jsonl.gz`: transcript completi e stati finali privati dell'arbitro,
  verificabili con `python -m domino_engine audit docs/results/TOURNAMENT_EVENTS.jsonl.gz`.
- `TOURNAMENT_SUMMARY.json`: W/D/L, punti e intervalli raggruppati per deal.
- `BENCHMARK_RESULTS.csv/.json`: 150 posizioni indipendenti, seed 30000–30149.
- `EVIDENCE_INTEGRITY.json`: corrispondenza metriche/transcript e bilanciamento.
- `PACKAGING_VALIDATION.json`: wheel, checksum e installazione fuori dal checkout.
- `development/`: 1.000 partite su seed di sviluppo 1000–1024, non usate per dichiarare la forza indipendente.
- `logs/`: output effettivo dei comandi della verifica finale, senza omissione di fallimenti.

I tempi sono osservazioni della macchina dichiarata, non valori riproducibili bit
per bit. Le scelte e i risultati sono riproducibili quando il cutoff temporale
non scatta. I file di gioco virtuale contengono informazioni private dell'arbitro:
non sono input del decisore e non descrivono segreti di una partita fisica.
