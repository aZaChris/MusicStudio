# Stripe Connect: il pagamento va allo studio, non a noi

## TL;DR

MusicStudio non vuole tenere i soldi di nessuno. Con Stripe Connect ogni studio ha un **suo conto Stripe** e il genitore paga direttamente lì. Noi salviamo solo l'id del conto e il suo stato. Nessuna commissione, nessun trasferimento. La funzione è costruita, provata con finti e con un po' di sandbox, ma **spenta**: la accende il proprietario.

## Il problema reale

Dalla fase 3 un genitore può pagare un pacchetto online con Stripe Checkout. C'era però un difetto di fondo: il denaro finiva sul conto Stripe **della piattaforma**, cioè sul conto di chi gestisce MusicStudio.

Questo è un problema serio, per tre motivi. Il primo: il progetto dice che MusicStudio è gratuito e non tiene denaro. Il secondo: chi incassa soldi per conto di altri entra in un terreno regolato. Il terzo: lo studio deve poi ricevere quei soldi in qualche modo, e questo vorrebbe dire fare noi i bonifici.

Il proprietario vuole una cosa semplice: che un genitore possa pagare come si paga oggi, con carta e portafogli, e che il denaro arrivi **direttamente allo studio**.

## Come funziona, con un'analogia

Pensa a un mercato coperto. Ogni banco ha la sua cassa. Il mercato (la piattaforma) mette il tetto, le luci e il cartello all'ingresso, ma **non tocca gli incassi**: il cliente paga al banco e il banco tiene i soldi.

In Stripe Connect il "banco" è il **conto collegato** dello studio. Il "cliente" è il genitore. La piattaforma è il mercato. Quando il genitore paga, Stripe crea il pagamento *sul conto dello studio*. Si chiama **pagamento diretto**.

Il conto collegato lo crea lo studio stesso, sulla pagina di Stripe. Lì inserisce chi è, il suo IBAN e accetta i termini. Noi non vediamo niente di tutto questo.

## Come l'abbiamo applicato in MusicStudio

Il codice sta quasi tutto in `backend/apps/payments/`. Le regole del progetto restano: le chiamate a Stripe stanno in `gateway.py` e basta, le scritture in `services.py`, le letture in `selectors.py`.

**Il conto dello studio.** Una tabella, `StudioPaymentAccount`, con una riga per studio: l'id del conto Stripe e uno stato (in corso, servono informazioni, attivo, limitato, scollegato). Niente documenti, niente dati bancari, niente nomi.

**L'attivazione.** Il titolare preme "Apri il mio conto su Stripe". Noi creiamo il conto con l'API nuova di Stripe (Accounts v2) con la dashboard completa: lo studio vede il suo Stripe. Poi chiediamo a Stripe un link temporaneo e mandiamo il titolare lì. Due clic insieme creano un solo conto: la riga dello studio viene bloccata mentre si parla con Stripe.

**Lo stato.** Lo ricaviamo da ciò che Stripe dice, mai da ciò che supponiamo:

```python
def state_from_account(info):
    if info.closed:
        return State.DISCONNECTED
    if info.card_payments == "active":
        return State.ACTIVE
    if info.card_payments == "pending":
        return State.IN_PROGRESS
    if info.open_requirements > 0:
        return State.INFORMATION_NEEDED
    ...
```

Solo "attivo" permette di incassare. Per i conti di questo tipo Stripe non ci manda eventi sullo stato, quindi lo rileggiamo quando il titolare torna dalla pagina di Stripe e ogni ora con un'attività in background.

**Il pagamento diretto.** Il punto chiave è una sola opzione: l'intestazione `Stripe-Account` con l'id del conto dello studio.

```python
def _options(*, idempotency_key=None, stripe_account=None):
    options = {}
    if idempotency_key:
        options["idempotency_key"] = idempotency_key
    if stripe_account:
        options["stripe_account"] = stripe_account
    return options
```

La Checkout Session nasce così sul conto dello studio. Non mandiamo mai `application_fee_amount` (una commissione), `on_behalf_of` o un trasferimento: un test legge il codice e fallisce se qualcuno li aggiunge.

**Gli eventi.** Quando il genitore paga, Stripe avvisa un secondo endpoint webhook, quello dei conti collegati, che ha un segreto suo. L'evento porta il campo `account`: da lì sappiamo di quale studio si tratta. Un evento di un conto non può mai chiudere il tentativo di un altro.

**L'interruttore.** `ONLINE_PAYMENTS_ENABLED` è spento di default. Spento, le rotte del conto rispondono 404, nessun pacchetto è pagabile online e il portale non mostra nulla.

Prima di questa fase, `start_checkout` creava la sessione sul conto della piattaforma. Ora rifiuta (409) se lo studio non ha un conto attivo.

## Alternative considerate

Il piano partiva da un conto **Standard** della vecchia API. L'ho provato sul sandbox: Stripe lo rifiuta per una piattaforma nuova e chiede di usare Accounts v2. Il codice è passato alla nuova API cambiando solo il gateway: è il vantaggio di tenere Stripe in un posto solo.

Un conto **Express** o **Custom** costa di più per ogni account e ci darebbe più responsabilità sui dati dello studio. Un pagamento **indiretto** (destination charge, o il modello "Marketplace") farebbe passare il denaro dal conto della piattaforma: esattamente ciò che vogliamo evitare.

Ho anche provato a completare il conto via API, per non far perdere tempo al proprietario. Stripe lo rifiuta: i termini li accetta solo il titolare, sulla sua pagina. Ed è giusto così.

## Errori comuni e trade-off

L'errore più facile è pensare che "senza commissioni" basti a non toccare denaro. Non basta: conta dove nasce il pagamento. Un pagamento che nasce sul conto della piattaforma e poi viene girato è un'altra cosa.

Un altro errore è dare per scontato PayPal. Stripe lo elenca per i conti collegati in Italia, ma come funzione su invito, e una segnalazione dice che in test viene rifiutato nei pagamenti diretti. **Io non l'ho provato.** Le carte e gli altri metodi che Stripe abilita per il conto funzionano; PayPal dipende da Stripe.

Il costo per la piattaforma: il listino pubblico dice zero se è Stripe a fatturare le commissioni agli studi, ma non dice se i parametri della nuova API corrispondono esattamente a quel modello. Va controllato nella Dashboard prima dei soldi veri.

Il trade-off principale: l'attivazione richiede una persona sulla pagina di Stripe. Non possiamo farla al posto dello studio, ed è la scelta giusta per la privacy.

## Cosa è provato e cosa no

Provato sul sandbox: la chiave, il modello "Piattaforma", il rifiuto dei conti vecchi, la creazione del conto nuovo, il link di attivazione, il rifiuto dell'accettazione dei termini via API. Provato con finti: tutto il resto del codice (1166 test del backend, 140 del portale). **Non provato con Stripe vero**: un pagamento diretto, un rimborso, una contestazione, l'arrivo degli eventi veri. Serve un conto di prova che finisca l'attivazione.

## Come lo spiegheresti a un colloquio

Volevo che la mia piattaforma non toccasse mai i soldi degli studi, quindi ho usato Stripe Connect con pagamenti diretti: il pagamento nasce sul conto collegato dello studio, non sul mio. Salvo solo l'id del conto e uno stato ricavato da ciò che Stripe riferisce, perché i dati personali restano su Stripe. Ho dovuto cambiare tipo di conto in corsa: quello che avevo pianificato era stato dichiarato obsoleto e il sandbox lo rifiutava, e tenere Stripe in un solo modulo ha ridotto il cambio a un file. Ho messo tutto dietro un interruttore spento, perché andare con soldi veri richiede una decisione e documenti legali. E ho scritto chiaramente cosa avevo provato davvero e cosa no.

## Cinque domande di autoverifica

**1. Perché il vecchio pagamento della fase 3 contraddiceva il progetto?**
Perché il denaro finiva sul conto della piattaforma, mentre il principio è che MusicStudio non tiene denaro.

**2. Che cos'è un pagamento diretto?**
Un pagamento creato direttamente sul conto collegato dello studio, con l'intestazione `Stripe-Account`. Il denaro non passa dalla piattaforma.

**3. Cosa salviamo del conto dello studio?**
Solo l'id del conto Stripe e uno stato. Documenti, dati bancari e requisiti restano su Stripe.

**4. Perché lo stato si rilegge ogni ora?**
Perché per i conti della nuova API Stripe non ci manda eventi sullo stato: senza il giro orario un conto bloccato da Stripe resterebbe "attivo" da noi.

**5. Cosa impedisce di accendere i pagamenti veri per sbaglio?**
Tre cose: l'interruttore spento di default, il blocco all'avvio con una chiave `sk_live_`, e il fatto che servono un emendamento alla costituzione e i termini d'uso.
