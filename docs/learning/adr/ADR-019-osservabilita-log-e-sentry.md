# ADR-019: Osservabilità con log JSON, request id e Sentry

- Stato: accettato
- Data: 2026-11-09

## Contesto

Fino alla fase 3 i log erano righe di testo libero, senza un modo per legare tra loro le righe della stessa richiesta. Un errore in produzione si scopriva leggendo la console del server, oppure quando un utente si lamentava. E un errore dentro un task Celery non si poteva collegare alla richiesta che lo aveva messo in coda.

## Decisione

- **Request id.** Un middleware, il primo della catena, assegna a ogni richiesta un identificativo. Se il proxy ne manda uno valido nell'header `X-Request-ID` lo riusa, altrimenti ne crea uno nuovo. "Valido" significa fino a 64 caratteri tra lettere, numeri e trattino: niente spazi o a capo, così nessuno può iniettare righe false nei log. L'id torna al client nella risposta.
- **ContextVar.** L'id vive in una `ContextVar`: è corretta per ogni thread e per ogni coroutine, senza passarla a mano.
- **Una riga di accesso per richiesta**, con metodo, route (lo schema dell'URL, non l'URL con gli id), stato, durata in millisecondi, utente e studio. Studio e utente arrivano dal `TenantContext` già calcolato, quindi senza query in più.
- **Celery.** L'id viaggia negli header del messaggio del task e viene ripristinato quando il task parte. I log del task hanno lo stesso id della richiesta.
- **JSON in produzione**, testo leggibile in sviluppo. Il formatter è scritto con la libreria standard, in circa 25 righe.
- **Sentry**, attivo solo se c'è `SENTRY_DSN`. `send_default_pii=False`. Un hook `before_send` toglie gli header `Authorization`, `Cookie` e `Stripe-Signature`, i cookie, i corpi degli endpoint di autenticazione e dei webhook, e sostituisce le email nei messaggi. Restano come tag `request_id`, `studio_id` e `user_id`. Le tracce di performance sono a 0 per non consumare la quota gratuita.
- Il comando `manage.py raise_test_error` verifica la configurazione dopo un deploy, senza aprire un endpoint che chiunque potrebbe chiamare.

## Alternative scartate

- **structlog o python-json-logger**: una dipendenza in più per poche righe di codice.
- **Il log di accesso di gunicorn**: non conosce il request id, né l'utente, né lo studio.
- **GlitchTip self-hosted**: compatibile con Sentry, ma è un altro servizio da far girare e da salvare nei backup.
- **Email agli amministratori per ogni errore** (`AdminEmailHandler`): nessun raggruppamento degli errori uguali, e i dati personali finiscono nelle caselle di posta.

## Conseguenze

- Dato un id preso da una risposta o da un errore in Sentry, si trovano tutte le righe di log di quella richiesta e dei suoi task.
- L'header `X-Request-ID` del client viene accettato. Un client potrebbe riusare lo stesso id per richieste diverse: confonde solo i suoi log, non i dati.
- Se Sentry non è raggiungibile, l'API funziona comunque e gli errori restano nei log.
