# Log strutturati, request id e Sentry

## TL;DR

In produzione non puoi mettere un `print` e guardare la console. Devi capire cosa è successo dopo, a partire da quello che il sistema ha scritto. In MusicStudio ogni richiesta ha un identificativo, il request id, che finisce in ogni riga di log, anche in quelle dei task Celery che la richiesta mette in coda. I log di produzione sono in JSON, una riga per evento. Gli errori arrivano a Sentry, ripuliti da token, cookie ed email.

## Il problema reale

Fino alla fase 3 i log erano righe di testo libero. Con tre processi web e un worker che scrivono insieme, le righe di richieste diverse si mescolano. Se un utente dice "alle 10 la dashboard mi ha dato errore", non c'è modo di trovare le righe di **quella** richiesta tra centinaia.

Poi ci sono i task Celery. Una richiesta mette in coda un task, che fallisce un secondo dopo in un altro processo. Nei log non c'era niente che legasse il task alla richiesta.

E infine gli errori. Senza uno strumento che li raccolga, un errore in produzione lo scopri quando un utente si lamenta.

## Come funziona

Pensa a un ospedale. Quando arrivi al pronto soccorso ti mettono un braccialetto con un numero. Ogni esame, ogni referto, ogni passaggio di reparto riporta quel numero. Se un medico vuole ricostruire la tua giornata, cerca il numero e trova tutto, in ordine. Il **request id** è quel braccialetto.

Il **log strutturato** è il modulo prestampato al posto dei fogli scritti a mano. Ogni riga è un oggetto JSON con campi fissi: ora, livello, messaggio, request id, durata. Un sistema di raccolta dei log può filtrare per campo: "tutte le richieste con stato 500 dello studio 7 nell'ultima ora". Con il testo libero si fanno solo ricerche di parole.

**Sentry** è il reparto che riceve una segnalazione per ogni errore. Raggruppa gli errori uguali, ti dice quante volte sono successi e da quando, e manda un avviso. Ma riceve i dati della richiesta, e qui serve attenzione: non deve ricevere password, token o email.

## Come lo abbiamo applicato in MusicStudio

Tutto sta in `backend/apps/common/logging.py`, con la sola libreria standard.

**Il request id.** `RequestIdMiddleware` è il primo middleware. Se il proxy manda un header `X-Request-ID` valido lo riusa, altrimenti ne crea uno nuovo. "Valido" significa fino a 64 caratteri tra lettere, numeri e trattino. Niente spazi e niente a capo: un client non può iniettare righe false nei log. L'id torna nella risposta, così il client lo può citare quando segnala un problema.

L'id vive in una `ContextVar`, una variabile che vale per il thread o la coroutine corrente. Un filtro di logging, `RequestIdFilter`, lo aggiunge a ogni riga.

**La riga di accesso.** Alla fine di ogni richiesta il middleware scrive una riga con metodo, route, stato, durata in millisecondi, utente e studio. La route è lo schema dell'URL, `api/v1/lessons/`, non l'URL con l'id, così le richieste si raggruppano. Studio e utente vengono dal `TenantContext` già calcolato: nessuna query in più.

**Celery.** Quando un task viene messo in coda, l'id corrente viene copiato negli header del messaggio. Quando il task parte, viene rimesso nella `ContextVar`:

```python
def stamp_task_headers(headers=None, **_):
    current = request_id_var.get()
    if headers is not None and current != "-":
        headers.setdefault("request_id", current)
```

Abbiamo anche detto a Celery di non sostituire la configurazione di logging di Django (`CELERY_WORKER_HIJACK_ROOT_LOGGER = False`). Altrimenti i worker scriverebbero nel loro formato, senza JSON e senza id.

**Il JSON.** In produzione il formatter `JsonFormatter` scrive un oggetto per riga. Anche un traceback finisce dentro un campo, su una sola riga. In sviluppo resta il testo leggibile. Il log di accesso di gunicorn è stato tolto: la nostra riga è più ricca.

**Un bug trovato con gunicorn vero.** Provando il server con il load test, la riga di errore di Django (`django.request`, per le risposte 4xx e 5xx) usciva con request id `-`. Il motivo: Django scrive quella riga dopo che tutti i middleware hanno finito, e il nostro middleware aveva già azzerato l'id. Ora l'id si azzera sul segnale `request_finished`, che arriva quando la risposta è chiusa. Un test lo verifica.

**Sentry.** `backend/apps/common/sentry.py`. Si attiva solo se `SENTRY_DSN` è impostata: senza, l'API funziona uguale. `send_default_pii=False` e un hook `before_send` che toglie gli header `Authorization`, `Cookie` e `Stripe-Signature`, i cookie, i corpi degli endpoint di login e webhook, e sostituisce le email nei messaggi. Restano tre tag: request id, studio e utente. Per provare la configurazione dopo un deploy c'è il comando `manage.py raise_test_error`, invece di un endpoint che chiunque potrebbe chiamare.

## Alternative considerate

**structlog o python-json-logger.** Ottime librerie, ma per 25 righe di formatter non serve una dipendenza.

**Il log di accesso di gunicorn.** Non conosce request id, utente e studio.

**GlitchTip self-hosted.** Compatibile con Sentry, ma è un servizio in più da mantenere e da salvare nei backup.

**Email agli amministratori per ogni errore.** Nessun raggruppamento, e i dati personali finiscono nelle caselle di posta.

## Errori comuni e trade-off

- **Fidarsi dell'header del client senza controllarlo.** Un a capo nell'id permetterebbe di scrivere righe di log false.
- **Mandare tutto a Sentry.** Con `send_default_pii=True` arrivano IP, cookie e utenti. Su un'app con dati di minori è inaccettabile.
- **Azzerare il contesto troppo presto.** È il bug che abbiamo trovato: una riga scritta dopo la fine del middleware perde l'id.
- **Tracce di performance al 100%.** Consumano in un attimo la quota gratuita di Sentry. Le teniamo a 0.
- **Trade-off:** un client può mandare lo stesso id per richieste diverse. Confonde solo i suoi log, non tocca i dati di nessuno.

## Come lo spiegheresti a un colloquio

Ogni richiesta riceve un request id, che riuso dal proxy solo se è sicuro da scrivere nei log, e che restituisco nella risposta. L'id sta in una ContextVar, un filtro lo aggiunge a ogni riga, e passa nei task Celery attraverso gli header del messaggio. In produzione i log sono JSON, una riga per evento, con una riga di accesso per richiesta che include route, stato, durata, utente e studio. Gli errori vanno a Sentry senza dati personali, grazie a un hook che toglie token, cookie ed email. Provando con gunicorn vero ho trovato che la riga di errore di Django perdeva l'id, perché viene scritta dopo i middleware, e l'ho corretto azzerando l'id sul segnale di fine richiesta.

## Domande di autoverifica

1. **A cosa serve il request id?**
   A trovare tutte le righe di log di una stessa richiesta, e dei task che ha messo in coda, tra quelle di tutte le altre.

2. **Perché una ContextVar e non una variabile globale?**
   Perché ogni thread o coroutine ha il suo valore. Con una globale, due richieste contemporanee si sovrascriverebbero l'id.

3. **Come arriva il request id dentro un task Celery?**
   Viene copiato negli header del messaggio quando il task è messo in coda, e rimesso nella ContextVar quando il task parte.

4. **Perché non accettiamo qualsiasi `X-Request-ID` dal client?**
   Perché un id con un a capo permetterebbe di inserire righe false nei log. Accettiamo solo lettere, numeri e trattini, fino a 64 caratteri.

5. **Cosa toglie `before_send` prima di inviare un errore a Sentry?**
   Gli header con credenziali, i cookie, i corpi degli endpoint di login e webhook, e le email nei messaggi.
