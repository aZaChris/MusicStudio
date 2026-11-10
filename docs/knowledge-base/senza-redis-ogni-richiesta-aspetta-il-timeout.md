# KB: Senza Redis ogni richiesta aspettava secondi

## Sintomo
Verifica end-to-end dell'app mobile contro Django in locale (10 novembre 2026): 3 passi su 9, il login non arrivava mai alla home. Nel log di Django molti `TimeoutError` dai throttle.

## Causa radice
Su questa macchina Redis non è installato. I throttle di DRF "falliscono aperti" quando Redis è giù (ADR-017), ma prima aspettano il timeout di connessione: ogni richiesta era di secondi più lenta, e l'interfaccia superava le attese dello script.

## Come l'abbiamo confermata
Traceback nel log (`redis.exceptions.TimeoutError` da `throttling.py`); con una cache in memoria la stessa prova è passata 9 su 9.

## Risoluzione
Per le prove locali, un file di settings fuori dal repository che usa una cache in memoria. In produzione Redis c'è.

## Lezione per il futuro
"Fallire aperti" protegge la disponibilità, ma non la velocità: un servizio che non risponde subito costa un timeout per richiesta. È un costo misurabile della scelta, da sapere quando Redis ha problemi in produzione.

## Riferimenti
- `docs/knowledge-base/redis-giu-e-throttling.md`
- `docs/learning/verifica-web-end-to-end.md`
