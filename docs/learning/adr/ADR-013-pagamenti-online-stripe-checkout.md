# ADR-013: Pagamenti online con Stripe Checkout, solo in modalità test

- Stato: accettato
- Data: 2026-11-06

## Contesto

Fino alla fase 2 i pagamenti erano solo registrati a mano. La constitution riapre l'integrazione di un gateway di pagamento nella fase 3, ma solo in modalità test. Un genitore deve poter pagare un pacchetto di lezioni online.

## Decisione

- **Stripe Checkout Sessions**, pagina ospitata da Stripe, `mode=payment`, prezzo inline (`price_data`) per ogni pacchetto. È l'API che Stripe raccomanda per i pagamenti singoli "on session". La pagina ospitata tiene i dati delle carte fuori dai nostri server.
- **Nessun `payment_method_types`**: i metodi di pagamento sono "dinamici" e si configurano dalla Dashboard di Stripe.
- **Un solo modulo parla con Stripe**: `backend/apps/payments/gateway.py`, con un'istanza di `StripeClient` (mai la chiave globale). Il resto del codice usa funzioni e dati semplici. Nei test il modulo è sostituito da un finto.
- **Ogni tentativo è una riga** `CheckoutSession` (id UUID) creata prima di chiamare Stripe. La chiamata porta la chiave di idempotenza `checkout-<uuid>`.
- **Doppio clic**: la riga del pacchetto è bloccata (`select_for_update`) per tutta l'operazione, chiamata a Stripe compresa. La seconda richiesta aspetta e riceve lo stesso tentativo aperto.
- **Solo modalità test**: una chiave che non inizia con `sk_test_` o `rk_test_` blocca l'avvio. Senza chiave, il checkout risponde 503 e il resto dell'API funziona. Si raccomanda una chiave ristretta (`rk_test_`) con il solo permesso "Checkout Sessions: write", in una sandbox Stripe dedicata.
- **Il pagamento si registra solo dal webhook**, mai dalla pagina di successo (ADR-014).

## Alternative scartate

- **PaymentIntents con Payment Element**: interfaccia personalizzata che i client oggi non hanno.
- **Payment Links**: statici, non portano in modo pulito l'id del nostro tentativo.
- **Charges API**: deprecata.
- **Chiamare Stripe fuori dalla transazione**: niente lock durante la rete, ma due richieste simultanee aprirebbero due pagine di pagamento.

## Conseguenze

- Il lock sul pacchetto dura quanto la chiamata a Stripe (di solito meno di un secondo). È accettabile a questi volumi, ma è un compromesso.
- Nessun account Stripe è stato usato durante lo sviluppo. Le chiamate sono provate con un finto, mentre le firme dei webhook sono generate con l'algoritmo vero e verificate dall'SDK vero. La prova end-to-end con una sandbox è descritta in `specs/004-celery-payments/quickstart.md`.
