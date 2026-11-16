# ADR-037: Il pagamento online va sul conto Stripe dello studio

- Stato: accettato (funzione costruita ma spenta di default)
- Data: 2026-11-16

## Contesto

Dalla fase 3 un genitore può pagare un pacchetto con Stripe Checkout. Ma il denaro finirebbe sul conto Stripe **della piattaforma**, cioè del proprietario di MusicStudio. Questo contraddice il principio dichiarato dalla fase 8: MusicStudio è gratuito, gli studi sono autonomi e la piattaforma non tiene né muove denaro.

Il proprietario vuole che l'app possa essere usata per pagamenti come si fa oggi (carte e, dove il fornitore li rende disponibili, portafogli come PayPal), con il denaro che va **direttamente** allo studio e nessuna commissione per la piattaforma.

La costituzione (principio IV) ammette l'integrazione dei pagamenti solo in **modalità test**. Il proprietario ha deciso di costruire la funzione ma di tenerla spenta finché non decide altro.

## Decisione

- Ogni studio ha un **conto collegato** di Stripe, creato con l'API nuova (Accounts v2): dashboard completa (lo studio vede il suo Stripe), configurazione "esercente" con la capacità di incassare con carta, commissioni e perdite a carico di Stripe. MusicStudio salva solo l'id del conto e uno stato (`StudioPaymentAccount`); documenti, dati bancari e requisiti restano su Stripe.
- L'attivazione avviene sulla **pagina ospitata da Stripe**. Il titolare la apre da un link temporaneo. I termini di servizio li accetta lui, lì: con la raccolta dei dati a carico di Stripe, un'accettazione via API viene rifiutata (provato).
- Il pagamento è un **pagamento diretto**: la Checkout Session nasce sul conto dello studio (intestazione `Stripe-Account`). Nessun `application_fee_amount`, nessun `on_behalf_of`, nessun trasferimento. Un test sul codice vieta questi parametri.
- Lo stato del conto è quello che Stripe riferisce: attivo solo se la capacità di incassare è attiva. Non arrivano eventi sullo stato del conto per i conti v2, quindi lo stato si rilegge **a richiesta** (quando il titolare torna da Stripe, dal pulsante "Controlla lo stato") e **ogni ora** per tutti i conti non scollegati.
- Un interruttore, `ONLINE_PAYMENTS_ENABLED`, **spento di default**. Spento: le rotte del conto rispondono 404, nessun pacchetto è pagabile online e il checkout rifiuta.
- Una chiave `sk_live_` continua a bloccare l'avvio. Andare in produzione con soldi veri richiede una decisione del proprietario, un emendamento alla costituzione e i termini d'uso: non fa parte di questa fase.

## Alternative scartate

- **Conto Standard v1.** Era la scelta iniziale del piano. Provata sul sandbox: Stripe rifiuta di creare conti v1 per una piattaforma nuova e rimanda ad Accounts v2.
- **Express o Custom.** Più costi per account e più responsabilità (dati e verifiche) a carico della piattaforma.
- **Destination charge, o il modello "Marketplace".** Il denaro passerebbe prima dal conto della piattaforma: è proprio ciò che si vuole evitare.
- **Completare il conto via API.** Provato e rifiutato da Stripe (accettazione dei termini non consentita). Va comunque bene così: non raccogliamo nulla.
- **Ascoltare gli eventi v2 dello stato del conto.** Hanno un meccanismo diverso dai webhook normali. Per questa fase si preferisce rileggere il conto; gli eventi v2 restano un lavoro futuro.
- **Un secondo fornitore (PayPal diretto).** Non serve: con Stripe i portafogli dipendono da ciò che Stripe abilita per quel conto.

## Conseguenze

- **PayPal non è garantito.** Stripe lo elenca per i conti collegati in Italia, ma come disponibile su invito, e una segnalazione di uno sviluppatore dice che in test viene rifiutato nei pagamenti diretti. Non l'ho provato: dipende da un conto di prova che finisca l'attivazione sulla pagina di Stripe.
- **Costi.** Il listino pubblico di Stripe dice che, se è Stripe a fatturare le commissioni ai conti collegati, la piattaforma non paga nulla per conto o per bonifico. Che i parametri v2 usati corrispondano esattamente a quel modello non è confermato dalla pagina: va controllato nella Dashboard prima dei soldi veri.
- **Cosa è provato e cosa no.** Provato sul sandbox: la chiave, il modello "Piattaforma", il rifiuto dei conti v1, la creazione di un conto v2 con dashboard completa, il link di attivazione, il rifiuto dell'accettazione dei termini via API. **Non provato** con Stripe vero: un pagamento diretto completo, un rimborso, una contestazione, l'arrivo degli eventi con il campo `account`. Il resto del codice è provato con un finto gateway e con eventi che hanno la forma indicata dalla documentazione, non con eventi catturati.
- L'attivazione richiede una persona sulla pagina di Stripe (con i dati di test in modalità test).
- Chi riceve il denaro è lo studio: commissioni, rimborsi e contestazioni sono suoi, e i termini d'uso (da far scrivere) devono dirlo.
