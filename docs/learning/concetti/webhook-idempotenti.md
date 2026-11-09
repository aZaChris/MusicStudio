# Webhook idempotenti

## TL;DR

Un webhook è una richiesta HTTP che un servizio esterno, per noi Stripe, manda al nostro server quando succede qualcosa, per esempio un pagamento completato. Le notifiche possono arrivare due volte, in ritardo, fuori ordine, o essere false. In MusicStudio ogni notifica viene verificata con la firma, salvata una volta sola con il suo id, confermata subito con un 200 ed elaborata in background in modo idempotente. Una riconciliazione oraria recupera le notifiche perse.

## Il problema reale

Quando un genitore paga un pacchetto, il pagamento avviene sulla pagina di Stripe, non sulla nostra. Come facciamo a saperlo? Stripe ce lo dice con un webhook: una richiesta POST al nostro endpoint `/api/v1/webhooks/stripe/`.

Sembra semplice, ma ci sono quattro trappole.

**Duplicati.** Se rispondiamo lentamente o con un errore, Stripe riprova. A volte manda la stessa notifica due volte anche senza errori. Se ogni notifica creasse un pagamento, avremmo pagamenti doppi.

**Notifiche false.** L'URL del webhook è pubblico e non richiede login. Chiunque lo conosca potrebbe mandare un falso "pagamento completato" e ottenere un pacchetto gratis.

**Ritardi e ordine.** Le notifiche non arrivano per forza nell'ordine in cui gli eventi sono successi.

**Notifiche perse.** Se il nostro server è giù abbastanza a lungo, Stripe smette di riprovare.

C'è anche una tentazione sbagliata: registrare il pagamento quando l'utente torna sulla "pagina di successo". Ma l'utente può pagare e chiudere il browser prima che la pagina si carichi. Stripe lo dice chiaramente: l'evasione dell'ordine va fatta dal webhook.

## Come funziona

Pensa a una banca che riceve bonifici con una distinta. Il cassiere controlla il timbro, cioè la firma, prima di accettare la distinta. Registra il numero della distinta in un registro: se arriva una copia con lo stesso numero, la riconosce e non accredita due volte. Rilascia la ricevuta subito, poi l'ufficio contabile fa l'accredito con calma. A fine giornata confronta il registro con l'estratto conto della banca mittente, per trovare distinte mai arrivate.

Ogni pezzo corrisponde a una tecnica.

**Firma.** Stripe calcola un HMAC-SHA256 di "timestamp + corpo della richiesta" con un segreto condiviso e lo manda nell'intestazione `Stripe-Signature`. Noi ricalcoliamo lo stesso valore. Se coincide, la notifica è autentica e non è stata modificata. Il timestamp impedisce di riutilizzare una notifica vecchia. La firma va calcolata sul **corpo grezzo**: se lo si trasforma in JSON e lo si riserializza, i byte cambiano e la firma non torna mai.

**Deduplica per id.** Ogni evento Stripe ha un id unico (`evt_...`). Lo salviamo con un vincolo unico. Un duplicato trova la riga esistente e si ferma.

**Rispondere subito.** Il 200 si manda appena l'evento è salvato. L'elaborazione avviene dopo, in background. Così Stripe non va in timeout e non riprova inutilmente.

**Elaborazione idempotente.** Il task rilegge lo stato dal database, blocca la riga, e se l'evento è già elaborato non fa niente.

**Riconciliazione.** Un controllo periodico chiede a Stripe lo stato dei tentativi rimasti aperti e li risolve con la stessa funzione del webhook.

## Come lo abbiamo applicato in MusicStudio

**La vista** è `backend/apps/payments/webhooks.py`. Non ha autenticazione utente né rate limiting: la sua sicurezza è la firma, e un 429 farebbe solo ritentare Stripe.

```python
try:
    event = gateway.verify_event(request.body, request.headers.get("Stripe-Signature"))
except gateway.InvalidWebhook:
    return Response({"detail": "Invalid signature."}, status=status.HTTP_400_BAD_REQUEST)
record_webhook_event(event)
return Response({"received": True})
```

**La verifica** è in `backend/apps/payments/gateway.py` e usa la funzione ufficiale dell'SDK di Stripe.

**Il salvataggio** è in `record_webhook_event` (`backend/apps/payments/services.py`): `get_or_create` sull'id dell'evento, e solo alla prima consegna `transaction.on_commit` accoda il task.

**L'elaborazione** registra il pagamento solo per `checkout.session.completed` o `checkout.session.async_payment_succeeded`, e solo se `payment_status` non è `unpaid`. Questo dettaglio viene dalle linee guida di Stripe: con metodi differiti, come l'addebito SEPA, la sessione si completa "non pagata" e l'esito arriva giorni dopo. `async_payment_failed` segna il tentativo come fallito, `expired` come scaduto. Gli altri tipi vengono salvati e ignorati.

**Un solo pagamento per tentativo** è una regola del database: `Payment.checkout` è un `OneToOneField`.

**I test** in `backend/apps/payments/tests/test_webhooks.py` costruiscono le firme con lo stesso algoritmo di Stripe, e le verifica l'SDK vero. Coprono: la stessa notifica tre volte (un pagamento), firma mancante o sbagliata (400, niente salvato), corpo manomesso (400), metodo differito, fallimento, scadenza, sessione sconosciuta, importo diverso dal prezzo, elaborazione ripetuta e riconciliazione.

## Alternative considerate

**Elaborare dentro la richiesta.** Più semplice, ma una risposta lenta fa ritentare Stripe, e i duplicati aumentano.

**Deduplicare solo controllando se il pagamento esiste.** Funziona per questo evento, ma non è una regola generale per gli eventi futuri.

**Allowlist degli IP di Stripe.** È una buona difesa in profondità. Nella fase 4 l'abbiamo aggiunta, nel codice invece che sul proxy, così è coperta dai test: vedi `concetti/ip-reale-dietro-proxy.md`.

**Polling senza webhook.** Chiedere a Stripe ogni minuto. Lento e costoso. Lo usiamo solo come rete di sicurezza, ogni ora.

## Errori comuni e trade-off

- **Verificare la firma su `request.data`.** Il corpo ricostruito ha byte diversi e la verifica fallisce sempre.
- **Registrare il pagamento sulla pagina di successo.** Si perdono i pagamenti di chi chiude il browser.
- **Considerare pagato ogni `checkout.session.completed`.** Con i metodi differiti il denaro non è ancora arrivato.
- **Rispondere con un errore agli eventi sconosciuti.** Stripe riproverebbe per giorni. Si risponde 200 e si ignora.
- **Trade-off:** salvare ogni evento occupa spazio, ma dà una traccia di controllo preziosa quando un genitore dice "ho pagato".

## Come lo spiegheresti a un colloquio

I webhook di Stripe possono arrivare duplicati, in ritardo, fuori ordine o falsificati, quindi li tratto in quattro passi. Verifico la firma HMAC sul corpo grezzo e rispondo 400 se non è valida. Salvo l'evento con il suo id unico, così un duplicato diventa un no-op, e rispondo subito 200. Un task Celery avviato dopo il commit lo elabora in modo idempotente, con la riga bloccata e un marcatore di "già elaborato", e un vincolo uno-a-uno garantisce un solo pagamento per tentativo. Registro il pagamento solo quando `payment_status` è pagato, anche sull'evento asincrono, e una riconciliazione oraria chiede a Stripe lo stato dei tentativi rimasti aperti.

## Domande di autoverifica

1. **Perché la firma va verificata sul corpo grezzo?**
   Perché la firma è calcolata sui byte esatti inviati da Stripe. Riserializzare il JSON li cambierebbe.

2. **Come evitiamo di registrare due volte lo stesso pagamento?**
   Con l'id unico dell'evento, con il marcatore "elaborato" nel task e con il vincolo uno-a-uno tra pagamento e tentativo.

3. **Perché non basta l'evento `checkout.session.completed`?**
   Perché con i metodi differiti la sessione si completa ma il denaro arriva dopo. Il pagamento si registra solo se `payment_status` non è `unpaid`, anche sull'evento `async_payment_succeeded`.

4. **Perché rispondiamo 200 anche agli eventi che non gestiamo?**
   Perché un errore farebbe ritentare Stripe per giorni senza motivo.

5. **A cosa serve la riconciliazione oraria?**
   A recuperare i pagamenti la cui notifica non è mai arrivata, chiedendo direttamente a Stripe lo stato dei tentativi scaduti.
