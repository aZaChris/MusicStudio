# ADR-031: Audit log scritto dai service

- Stato: accettato
- Data: 2026-11-11

## Contesto

Per dati di minori serve poter rispondere a "chi ha fatto cosa, e quando" per le azioni delicate: accessi, cambi di password, MFA, inviti, consensi, esportazioni, cancellazioni, pagamenti registrati. Il titolare dello studio deve poter vedere cosa è successo nel suo studio.

## Decisione

- Una nuova app `apps/audit` con il modello `AuditEntry` e una sola funzione, `audit.services.record(...)`, che prende azione, autore, bersaglio, studio, esito e pochi dati non personali.
- I **service** che compiono le azioni chiamano `record(...)` in modo esplicito. Si legge con una ricerca nel codice e si verifica con un test: `apps/audit/tests/test_coverage.py` fallisce se esiste un'azione senza un controllo.
- Una voce è **append-only**: `save()` su una voce esistente e `delete()` singolo sono rifiutati. Solo il task di conservazione cancella, in blocco, le voci più vecchie di 12 mesi.
- Nei metadati entrano solo valori semplici (numeri, testo, booleani) e mai nomi, email o password. Il bersaglio è un tipo e un id.
- Il titolare legge le voci del proprio studio con `GET /audit/`, filtrate per azione e data. Gli accessi non hanno uno studio, perciò il titolare vede quelli dei propri insegnanti e mai quelli dei genitori.
- L'id della richiesta viene copiato dal contesto dei log, così una voce si collega alle righe di log della stessa richiesta.

## Alternative scartate

- **Segnali Django**: scatterebbero anche per modifiche dall'admin e per le fixture, e non conoscerebbero l'autore.
- **`django-auditlog` o `simple-history`**: registrano ogni cambio di campo e copiano dati personali in un secondo posto, il contrario della minimizzazione.
- **Trigger nel database**: nessun autore e nessun id di richiesta.

## Conseguenze

- Chi scrive un nuovo service delicato deve ricordarsi di chiamare `record`: il test di copertura lo ricorda per le azioni già elencate, non per quelle nuove. Una nuova azione va aggiunta all'elenco `Action` e al test.
- Le voci sono dati personali (id di persone): per questo hanno una conservazione limitata a 12 mesi.
