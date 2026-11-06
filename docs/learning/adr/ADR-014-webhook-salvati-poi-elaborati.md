# ADR-014: Webhook Stripe: verifica, salva una volta, elabora in background

- Stato: accettato
- Data: 2026-11-06

## Contesto

Stripe comunica l'esito dei pagamenti con i webhook. Le notifiche possono arrivare due volte, in ritardo, fuori ordine, oppure essere falsificate da qualcuno che conosce l'URL. Se rispondiamo lentamente o con un errore, Stripe riprova per giorni.

## Decisione

1. **Verifica** della firma `Stripe-Signature` sul corpo grezzo della richiesta (`request.body`, mai `request.data`, che lo ricostruirebbe e cambierebbe i byte). Firma mancante o sbagliata: 400 e niente salvato.
2. **Salvataggio** dell'evento in `WebhookEvent` con `stripe_event_id` unico. Un duplicato trova la riga esistente e non fa altro.
3. **Risposta 200** subito.
4. **Elaborazione** in un task Celery avviato dopo il commit (`transaction.on_commit`). Il task blocca la riga dell'evento e, se `processed_at` è già valorizzato, non fa niente.
5. **Eventi gestiti**: `checkout.session.completed` e `checkout.session.async_payment_succeeded` registrano il pagamento solo se `payment_status` non è `unpaid` (i metodi differiti come l'addebito SEPA completano "unpaid" e confermano dopo); `async_payment_failed` segna il tentativo come fallito; `expired` come scaduto. Gli altri tipi sono salvati e ignorati.
6. **Un pagamento per tentativo**, garantito dal database: `Payment.checkout` è un `OneToOneField`.
7. **Riconciliazione oraria**: i tentativi ancora aperti dopo la scadenza vengono chiesti a Stripe e risolti con la stessa funzione. Copre i webhook persi.

## Alternative scartate

- **Elaborare dentro la richiesta**: una risposta lenta fa ritentare Stripe e genera altri duplicati.
- **Deduplicare solo su "il pagamento esiste già"**: funziona per questo evento, non come garanzia generale.
- **Fidarsi della pagina di successo**: l'utente può chiudere il browser dopo aver pagato.
- **Allowlist degli IP di Stripe**: utile come difesa in profondità, ma va fatta sul proxy. Rimandata alla fase 4.

## Conseguenze

- Il webhook non ha autenticazione utente né rate limiting: la sua sicurezza è la firma.
- Gli eventi restano nel database come traccia di controllo (audit).
- Se l'importo addebitato è diverso dal prezzo attuale del pacchetto, registriamo quello addebitato.
