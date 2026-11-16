# ADR-038: Un pagamento può avere più storni (rimborsi parziali)

- Stato: accettato
- Data: 2026-11-16

## Contesto

L'ADR-034 ha reso il registro di cassa affidabile: un pagamento incassato non si riscrive e si corregge con **uno storno**, una riga collegata all'originale con una relazione uno-a-uno, per l'importo intero.

Con i pagamenti online sul conto dello studio (ADR-037) lo studio può rimborsare dalla pagina di Stripe, anche **in parte** e anche **più volte**. Una contestazione persa è un altro modo in cui il denaro torna indietro. Uno storno unico e intero non basta più, e lasciare un rimborso parziale fuori dal registro farebbe mostrare denaro che lo studio non ha più.

## Decisione

- `Payment.reversal_of` diventa una **chiave esterna**: un pagamento può avere più righe di storno.
- Ogni riga di storno ha una **causa**: `manual` (correzione a mano, come nella fase 8), `refund` o `dispute`. Le righe che non sono storni valgono sempre `manual`.
- Le righe del fornitore portano l'id del rimborso o della contestazione di Stripe in `provider_ref`, **unico** nel database: una notifica ripetuta non può scrivere due volte.
- Lo storno **manuale** resta uno solo e per l'importo intero: lo garantisce un vincolo parziale (univoco su `reversal_of` dove la causa è `manual`). Si può fare solo se non esiste nessun altro storno.
- La somma degli storni di un pagamento **non supera mai** il suo importo. Non è esprimibile come vincolo del database, quindi si controlla nel service sotto il lock di riga dell'originale, come per i numeri delle ricevute. Un rimborso che la supererebbe non scrive nulla e viene segnalato allo studio.
- "Stornato" diventa una **somma**: un pagamento è stornato quando gli storni coprono l'importo. Un rimborso parziale abbassa il netto del registro e lascia il pacchetto pagato (le lezioni ci sono state); uno totale lo riapre.
- Uno storno del fornitore è datato **oggi**, mai a ritroso, come quello manuale: un mese già consegnato non cambia.
- Una contestazione è una riga a parte (`PaymentDispute`): "in contestazione" si legge da lì, perché il pagamento è definitivo e non si tocca. Se la contestazione è persa nasce lo storno con causa `dispute`; se è vinta non si storna nulla.

## Alternative scartate

- **Non gestire i rimborsi parziali**: il registro mostrerebbe denaro che lo studio non ha più, contro la specifica.
- **Un parziale come storno intero più un nuovo pagamento**: inventa un pagamento che non è mai avvenuto.
- **Una tabella `Refund` separata**: totali ed esportazioni avrebbero due fonti da sommare.
- **Un campo "importo rimborsato" sul pagamento**: riscriverebbe una riga definitiva.

## Conseguenze

- Il cambio ha toccato una decina di punti (selector dei pagamenti, serializer, elenco studenti, ricevute, esportazioni). La regola "stornato" sta in due funzioni sole (`with_reversals` e `not_fully_reversed`). La suite della fase 8 è passata invariata, tranne il rinomino di un accessorio in un test.
- Provato anche con 6 thread veri: rimborsi che insieme supererebbero l'importo non lo superano mai, lo stesso rimborso notificato 6 volte scrive una riga, e uno storno manuale contro un rimborso ha un solo vincitore.
- Il limite è dichiarato: la somma ≤ importo sta nel codice. Un test guarda che solo i service creino righe di `Payment`.
- Il contratto API aggiunge `reversed_amount`, `under_dispute` e `cause`. L'app mobile non li conosce ancora: la nota per l'app lo dice.
- La ricevuta è "annullata" solo quando il pagamento è stornato per intero.
