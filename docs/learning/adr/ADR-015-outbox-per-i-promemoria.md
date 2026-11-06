# ADR-015: Promemoria con una outbox transazionale (sostituisce ADR-008)

- Stato: accettato
- Data: 2026-11-06

## Contesto

Nella fase 1 (ADR-008) i promemoria erano "at most once": il task reclamava la lezione e poi mandava le email. Se il worker moriva tra le due cose, il promemoria era perso per sempre. Era un compromesso dichiarato, con la promessa di risolverlo nella fase 3.

## Decisione

- **Outbox**: una tabella `ReminderDelivery` con una riga per ogni coppia (lezione, genitore) e un vincolo `UNIQUE`.
- **Lo sweep** (ogni 15 minuti), in una sola transazione, segna la lezione come "elaborata" e inserisce le righe. Ripeterlo, o due sweep sovrapposti, non crea doppioni.
- **Ogni consegna ha il suo task**. Il task la reclama con un `UPDATE` condizionale, con un "lease" di 10 minuti, poi manda l'email e la segna come inviata. Se l'invio fallisce torna in attesa, e Celery riprova con attese crescenti (30, 60, 120, 240 secondi). Dopo 5 tentativi la consegna è "fallita".
- **Lease scaduto**: se un worker muore con la consegna in mano, dopo 10 minuti un altro la riprende.
- **Lezione annullata** nel frattempo: la consegna viene saltata.

## Alternative scartate

- **Restare "at most once"**: perde promemoria.
- **Riprovare l'intero sweep**: rimanderebbe email ai genitori già serviti.
- **Coda dedicata (RabbitMQ) con conferme**: più robusta, ma un servizio in più da gestire.

## Conseguenze

- La garanzia è "almeno una volta", senza doppioni per (lezione, genitore). Resta una finestra: un crash dopo che il server SMTP ha accettato l'email, ma prima di segnarla come inviata, porta a un secondo invio. Con SMTP "esattamente una volta" non è possibile: la finestra ora è di millisecondi.
- Le consegne fallite restano nel database, visibili nell'admin.
