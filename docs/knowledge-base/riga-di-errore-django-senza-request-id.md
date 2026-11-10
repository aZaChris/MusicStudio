# KB: La riga di errore di Django non aveva il request id

## Sintomo
Provando gunicorn vero con i log JSON (fase 4), la riga `django.request` per le risposte 4xx/5xx usciva con `"request_id": "-"`, mentre tutte le altre righe della richiesta avevano l'id.

## Causa radice
Il middleware azzerava l'id nel suo `finally`. Ma Django scrive `log_response` in `BaseHandler.get_response`, **dopo** che tutta la catena dei middleware è terminata: a quel punto l'id era già stato cancellato.

## Come l'abbiamo confermata
Lettura del sorgente di `django.core.handlers.base.get_response`; un test che, con il codice vecchio, trova `-` nella riga di errore.

## Risoluzione
L'id si azzera sul segnale `request_finished`, che arriva quando la risposta viene chiusa, dopo la riga di errore.

## Lezione per il futuro
"Dopo il middleware" non vuol dire "dopo la richiesta". Lo stato legato a una richiesta va pulito sull'evento che segna davvero la fine della richiesta.

## Riferimenti
- `backend/apps/common/logging.py`
- `docs/learning/concetti/log-strutturati-e-sentry.md`
