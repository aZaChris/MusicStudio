# ADR-016: Affidabilità dei task Celery

- Stato: accettato
- Data: 2026-11-06

## Contesto

Con le impostazioni predefinite, Celery conferma un task appena il worker lo riceve. Se il worker muore durante l'esecuzione, il task è perso. Con i pagamenti e i promemoria, perdere un task significa perdere denaro registrato o email.

## Decisione

- `task_acks_late`: il task si conferma solo alla fine.
- `task_reject_on_worker_lost`: se il processo del worker muore, il task torna in coda.
- `worker_prefetch_multiplier = 1`: ogni worker prende un task alla volta, così un task lungo non trattiene messaggi che altri worker potrebbero eseguire.
- Limiti di tempo soft e hard (60 e 90 secondi, configurabili).
- Solo JSON come formato dei messaggi.
- `visibility_timeout` di Redis a un'ora, più lungo del task più lungo, altrimenti Redis riconsegnerebbe un task ancora in esecuzione.
- Retry con backoff esponenziale dove l'errore è temporaneo.
- Un test fissa queste impostazioni, così non possono cambiare senza che qualcuno se ne accorga.

## Alternative scartate

- **Impostazioni predefinite**: perdono task.
- **Un broker diverso (RabbitMQ)**: conferme più precise, ma un servizio in più. Redis è già presente.

## Conseguenze

- **Un task può essere eseguito due volte** (dopo un crash, o se supera il visibility timeout). Per questo ogni task è idempotente: l'elaborazione dei webhook controlla `processed_at`, le consegne dei promemoria il loro stato, la riconciliazione lo stato del tentativo.
