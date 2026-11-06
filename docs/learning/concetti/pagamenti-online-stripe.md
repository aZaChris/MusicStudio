# Pagamenti online con Stripe Checkout

## TL;DR

Stripe è un servizio che gestisce pagamenti online. Con Stripe Checkout il pagamento avviene su una pagina ospitata da Stripe: i dati della carta non passano mai dai nostri server. In MusicStudio un genitore chiede un link di pagamento per un pacchetto di lezioni, paga su Stripe, e il pagamento viene registrato quando arriva il webhook. Tutto funziona solo in modalità test: con una chiave reale l'applicazione si rifiuta di partire.

## Il problema reale

Integrare un sistema di pagamento non è difficile da far funzionare. È difficile farlo funzionare **bene** quando qualcosa va storto. Il genitore fa doppio clic su "paga". La rete tra il nostro server e Stripe cade a metà di una richiesta. Il genitore paga e chiude il browser. Il prezzo del pacchetto cambia mentre la pagina di pagamento è aperta. Qualcuno prova a far credere al sistema che un pagamento sia avvenuto.

E c'è un rischio in più, legale e di sicurezza: gestire direttamente i numeri delle carte significa rientrare in regole molto severe (PCI DSS). Per un piccolo SaaS è un peso enorme.

## Come funziona

Pensa a un negozio che usa il terminale POS della banca. Il negoziante dice "sono 120 euro", il cliente paga sul terminale, e il negoziante non vede mai il PIN né il numero della carta. Riceve solo lo scontrino della banca: pagato o non pagato. Stripe Checkout è il terminale POS, in versione web.

Il flusso è questo:

1. Il nostro server crea una **Checkout Session** su Stripe: importo, valuta, descrizione, e un nostro riferimento.
2. Stripe restituisce un URL. Il client manda lì il genitore.
3. Il genitore paga sulla pagina di Stripe.
4. Stripe avvisa il nostro server con un **webhook**. Solo allora registriamo il pagamento.

Alcuni concetti chiave.

**Modalità test e sandbox.** Stripe ha un ambiente di prova in cui niente è vero: carte di test, nessun denaro reale. Le chiavi di test iniziano con `sk_test_` o `rk_test_`. Stripe consiglia di usare una **sandbox** dedicata per lo sviluppo e una per la CI, separate dall'account reale.

**Chiavi ristrette.** Una chiave segreta (`sk_`) può fare tutto. Una chiave ristretta (`rk_`) può fare solo ciò che le permetti. Per noi basta "Checkout Sessions: write". Se venisse rubata, farebbe molti meno danni.

**Chiave di idempotenza.** Ogni richiesta di creazione a Stripe può portare una chiave. Se Stripe riceve due richieste con la stessa chiave, esegue la prima e alla seconda restituisce lo stesso risultato. Protegge dai retry di rete.

**Metodi di pagamento dinamici.** Non si dice a Stripe "accetta solo carte". Si lascia che Stripe scelga i metodi più adatti al cliente, configurati dalla Dashboard. Alcuni metodi europei, come l'addebito SEPA, sono differiti: il pagamento si conferma giorni dopo.

## Come lo abbiamo applicato in MusicStudio

**L'endpoint** è `POST /api/v1/packages/{id}/checkout/`, in `backend/apps/packages/views.py`. Può chiamarlo chiunque veda il pacchetto: il genitore che paga, o l'insegnante che vuole mandargli il link. Il queryset filtrato per tenant fa sì che un pacchetto di un'altra famiglia dia 404.

**Il service** è `start_checkout` in `backend/apps/payments/services.py`:

- se il pacchetto è già pagato, risponde 409;
- blocca la riga del pacchetto e rilegge il prezzo dal database;
- se c'è un tentativo aperto e non scaduto, restituisce quello: un doppio clic non apre due pagine di pagamento;
- altrimenti crea una riga `CheckoutSession` con un UUID e chiama Stripe con la chiave di idempotenza `checkout-<uuid>`;
- se Stripe non risponde, la transazione si annulla e non resta nessun tentativo a metà, e il client riceve 503.

**Un solo modulo parla con Stripe**: `backend/apps/payments/gateway.py`. Usa un'istanza di `StripeClient`, come raccomanda Stripe, e non passa mai `payment_method_types`. La creazione della sessione, in breve:

```python
session = _client().v1.checkout.sessions.create(
    params={"mode": "payment", "line_items": [...], "metadata": {"checkout_id": checkout_id}, ...},
    options={"idempotency_key": idempotency_key},
)
```

**Solo modalità test.** In `backend/config/settings/base.py`, una chiave che non inizia con `sk_test_` o `rk_test_` blocca l'avvio con un errore. Un test lo verifica con una chiave `rk_live_`. Senza chiave, il checkout risponde 503 e il resto dell'API funziona.

**Chiavi fuori dal codice.** Un hook pre-commit rifiuta qualsiasi stringa che sembri una chiave Stripe o un segreto di webhook. L'ho provato con una chiave finta: il commit viene bloccato.

**Cosa non ho potuto provare.** Durante lo sviluppo non c'era un account Stripe. Le chiamate a Stripe nei test sono sostituite da un finto, mentre le firme dei webhook sono vere. La prova completa con una sandbox (carta `4242 4242 4242 4242`, `stripe listen` per i webhook) è descritta in `specs/004-celery-payments/quickstart.md`. Andrà fatta prima di considerare la funzione pronta.

## Alternative considerate

**PaymentIntents con Payment Element.** Permette una pagina di pagamento personalizzata dentro la nostra app. Serve un'interfaccia che i client oggi non hanno.

**Payment Links.** Link di pagamento creati dalla Dashboard, senza codice. Sono statici: non portano in modo pulito l'id del nostro tentativo.

**Charges API.** È la vecchia API di Stripe, deprecata.

**Un altro fornitore (PayPal, Satispay).** Stripe ha la documentazione e gli strumenti di test migliori, ed è lo standard di fatto per un portfolio.

## Errori comuni e trade-off

- **Registrare il pagamento sulla pagina di successo.** Chi chiude il browser non viene registrato.
- **Mettere la chiave nel codice.** È la causa principale di chiavi rubate.
- **Usare la chiave segreta completa** quando basta una ristretta.
- **Forzare `payment_method_types: ['card']`.** Riduce le conversioni e va contro le linee guida di Stripe.
- **Fidarsi del prezzo mandato dal client.** Il prezzo si legge sempre dal database, nel momento in cui si crea la sessione.
- **Trade-off:** la riga del pacchetto resta bloccata durante la chiamata a Stripe. Con pochi pagamenti va benissimo; con volumi alti si separerebbe la chiamata dalla transazione.

## Come lo spiegheresti a un colloquio

Per i pagamenti uso Stripe Checkout, la pagina ospitata da Stripe, così i dati delle carte non passano dai miei server. L'endpoint di checkout blocca la riga del pacchetto, riusa un tentativo aperto se c'è, e crea la sessione con una chiave di idempotenza legata all'UUID del tentativo, così doppi clic e retry di rete non creano due pagamenti. Il pagamento si registra solo dal webhook firmato, mai dalla pagina di successo. Tutta l'integrazione è in un modulo gateway con un `StripeClient`, sostituito da un finto nei test. L'applicazione accetta solo chiavi di test e un hook pre-commit blocca le chiavi nel codice.

## Domande di autoverifica

1. **Perché usare la pagina ospitata da Stripe invece di un form nostro?**
   Perché i dati delle carte non passano dai nostri server, e restiamo fuori dalla parte più pesante delle regole PCI.

2. **Cosa fa la chiave di idempotenza?**
   Se Stripe riceve due richieste con la stessa chiave, esegue solo la prima e alla seconda restituisce lo stesso risultato.

3. **Come gestiamo il doppio clic su "paga"?**
   Blocchiamo la riga del pacchetto: la seconda richiesta aspetta, poi trova il tentativo aperto e restituisce lo stesso link.

4. **Che differenza c'è tra una chiave `sk_` e una `rk_`?**
   La `sk_` può fare tutto. La `rk_` è ristretta ai permessi assegnati, quindi un furto fa meno danni.

5. **Perché non passiamo `payment_method_types`?**
   Perché Stripe sceglie dinamicamente i metodi più adatti, configurati dalla Dashboard, e le sue linee guida lo raccomandano.
