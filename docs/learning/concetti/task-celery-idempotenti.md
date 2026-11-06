# Task Celery idempotenti e affidabili

## TL;DR

Celery esegue lavori in background, fuori dalle richieste HTTP. Per non perdere lavori quando un worker muore, il task si conferma solo dopo averlo finito. Ma questo significa che un task può essere eseguito due volte. Quindi ogni task deve essere idempotente: eseguirlo due volte deve dare lo stesso risultato di una. In MusicStudio questo vale per l'elaborazione dei webhook di pagamento, per i promemoria e per la riconciliazione con Stripe.

## Il problema reale

Un task in background è codice che gira da solo, lontano dall'utente. Se fallisce, nessuno vede un errore sullo schermo. Per questo i task devono essere più robusti del codice delle viste, non meno.

Con le impostazioni predefinite, Celery conferma un messaggio appena il worker lo riceve. Il broker (per noi Redis) lo cancella. Se il worker si blocca o viene riavviato a metà lavoro, magari per un deploy, il task è perso. Nessuno lo rifà.

Nella fase 1 i promemoria delle lezioni avevano proprio questo problema, in una forma più sottile. Il task segnava la lezione come "ricordata" e poi mandava le email. Un crash tra le due cose significava un genitore senza promemoria, per sempre. Era un compromesso scelto e documentato, con la promessa di risolverlo in questa fase.

## Come funziona

Pensa a un corriere che consegna pacchi. Nel modo "veloce", il magazzino cancella il pacco dal registro appena il corriere lo prende. Se il furgone si rompe, il pacco è perso. Nel modo "sicuro", il magazzino lo cancella solo quando il corriere conferma la consegna. Se il furgone si rompe, il pacco torna disponibile per un altro corriere. Ma attenzione: se il corriere consegna e si rompe il telefono prima di confermare, un secondo corriere consegnerà lo stesso pacco. Per questo il destinatario deve saper riconoscere un pacco già ricevuto.

In Celery il modo "sicuro" si chiama **acks late**: conferma alla fine. Con `task_reject_on_worker_lost`, se il processo del worker muore, il messaggio torna in coda. Il prezzo è quello del corriere: lo stesso task può girare due volte.

La risposta è l'**idempotenza**. Un'operazione è idempotente se farla una o più volte produce lo stesso stato. "Imposta lo stato a pagato" è idempotente. "Crea un pagamento" no, a meno di controllare prima se esiste già.

Le tecniche principali:

- **Un marcatore di "già fatto"** nel database, controllato e scritto nella stessa transazione, con la riga bloccata.
- **Vincoli unici**: il database rifiuta il duplicato anche se due esecuzioni arrivano insieme.
- **Claim con UPDATE condizionale**: `UPDATE ... SET stato='in corso' WHERE id=? AND stato='in attesa'`. Solo una esecuzione modifica la riga, e solo quella procede.
- **Rileggere lo stato invece di fidarsi dei parametri**: il task riceve un id, non i dati, e legge dal database lo stato attuale.

Altre impostazioni importanti: `worker_prefetch_multiplier = 1`, così un worker non trattiene messaggi che non sta lavorando; limiti di tempo, così un task bloccato viene interrotto; e il `visibility_timeout` di Redis, che deve essere più lungo del task più lungo, altrimenti Redis consegna di nuovo un task ancora in esecuzione.

Per gli errori temporanei, come un database momentaneamente irraggiungibile o un server SMTP giù, si usano i **retry con backoff esponenziale**: si riprova dopo 30 secondi, poi 60, poi 120, fino a un massimo.

## Come lo abbiamo applicato in MusicStudio

**Le impostazioni** sono in `backend/config/settings/base.py`: `CELERY_TASK_ACKS_LATE`, `CELERY_TASK_REJECT_ON_WORKER_LOST`, `CELERY_WORKER_PREFETCH_MULTIPLIER = 1`, limiti di tempo e `visibility_timeout` di un'ora. Il test `backend/config/tests/test_celery.py` le fissa, così non cambiano per sbaglio.

**I task sono sottili.** In `backend/apps/payments/tasks.py` e `backend/apps/notifications/tasks.py` i task chiamano funzioni dei service. La logica e la sua idempotenza stanno nei service, dove si testano senza Celery.

**Elaborazione dei webhook.** `process_webhook_event` in `backend/apps/payments/services.py`:

```python
with transaction.atomic():
    event = WebhookEvent.objects.select_for_update().get(pk=event_pk)
    if event.processed_at is not None:
        return False
    ...
    event.processed_at = timezone.now()
    event.save(update_fields=["processed_at", "attempts"])
```

La riga è bloccata, il marcatore si controlla e si scrive nella stessa transazione. In più, il pagamento è legato al tentativo con un `OneToOneField`: anche con due eventi diversi per la stessa sessione, il database impedisce il secondo pagamento.

**Promemoria con una outbox.** Il vecchio task faceva tutto insieme. Ora lo sweep scrive solo "cosa va mandato", una riga `ReminderDelivery` per ogni coppia lezione-genitore, con un vincolo unico. Ogni consegna ha il suo task, che la reclama con un UPDATE condizionale e un "lease" di 10 minuti. Se l'invio fallisce, la consegna torna in attesa e Celery riprova con attese crescenti. Dopo 5 tentativi è "fallita". Se un worker muore con la consegna in mano, dopo 10 minuti un altro la riprende.

**Il prima e dopo.** Prima: promemoria "al massimo una volta", persi in caso di crash. Dopo: "almeno una volta", senza doppioni per lezione e genitore. I test in `backend/apps/notifications/tests/test_reminders.py` coprono il fallimento temporaneo (un'email sola dopo un retry), il fallimento permanente, il worker morto e lo sweep ripetuto tre volte.

**Dove resta un limite.** Se il server SMTP accetta l'email e il worker muore prima di segnarla come inviata, l'email partirà due volte. Con SMTP non esiste "esattamente una volta". La finestra però è di millisecondi.

## Alternative considerate

**Lasciare le impostazioni predefinite.** Più semplice, ma perde task.

**RabbitMQ al posto di Redis.** Conferme e riconsegne più precise. Ma è un servizio in più, e Redis è già nello stack.

**Un'unica transazione per tutto lo sweep, con lock su tutte le lezioni.** Terrebbe i lock per tutto il tempo dell'invio delle email.

**Disattivare i retry e affidarsi allo sweep successivo.** Rimanderebbe email a chi le ha già ricevute.

## Errori comuni e trade-off

- **Attivare acks late senza rendere idempotenti i task.** Si passa dal "perdere lavori" al "farli due volte".
- **Passare al task oggetti invece di id.** I dati possono essere vecchi quando il task parte. Si passa l'id e si rilegge.
- **Accodare un task dentro una transazione non ancora confermata.** Il worker potrebbe partire prima del commit e non trovare la riga. Si usa `transaction.on_commit`.
- **Retry senza limite.** Un errore permanente diventa un ciclo infinito.
- **Visibility timeout troppo corto.** Redis riconsegna un task ancora in corso.

## Come lo spiegheresti a un colloquio

Configuro Celery con acks late e reject on worker lost, così un task si conferma solo alla fine e torna in coda se il worker muore. La conseguenza è che un task può girare due volte, quindi tutti i miei task sono idempotenti: bloccano la riga, controllano un marcatore di "già fatto" e si appoggiano a vincoli unici nel database. Per i promemoria ho usato una outbox: lo sweep registra una consegna per ogni coppia lezione-genitore, e ogni consegna è un task con claim condizionale, lease e retry con backoff esponenziale. Il risultato è "almeno una volta" senza doppioni, con un'unica piccola finestra di duplicato dovuta a SMTP. Le impostazioni sono fissate da un test.

## Domande di autoverifica

1. **Cosa cambia con `task_acks_late`?**
   Il messaggio viene confermato solo quando il task finisce. Se il worker muore prima, il task torna in coda.

2. **Perché acks late richiede task idempotenti?**
   Perché lo stesso task può essere eseguito due volte, per esempio dopo un crash, e deve produrre lo stesso stato.

3. **Cos'è una outbox?**
   Una tabella in cui si registra, nella stessa transazione dei dati, "cosa va mandato". Un processo separato la legge e invia, con retry.

4. **A cosa serve il lease sulla consegna?**
   A permettere a un altro worker di riprendere una consegna lasciata a metà da un worker morto, ma solo dopo un tempo ragionevole.

5. **Perché si usa `transaction.on_commit` per accodare un task?**
   Perché il worker potrebbe partire prima che la transazione sia confermata e non trovare i dati che deve elaborare.
