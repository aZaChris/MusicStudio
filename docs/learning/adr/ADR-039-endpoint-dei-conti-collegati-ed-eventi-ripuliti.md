# ADR-039: Un secondo webhook per i conti collegati, e gli eventi si salvano ripuliti

- Stato: accettato
- Data: 2026-11-16

## Contesto

Con i pagamenti diretti (ADR-037) gli eventi di un pagamento, di un rimborso o di una contestazione nascono sul **conto dello studio**, non su quello della piattaforma. Stripe li consegna solo a un endpoint di tipo "Connected accounts", e ogni endpoint ha un segreto di firma suo.

Inoltre, fino alla fase 8, `WebhookEvent.payload` salvava l'evento **intero**. Una Checkout Session porta dentro nome, email e indirizzo di chi paga, e gli eventi dei conti collegati aggiungono altri dati. Era una copia di dati personali che nessuno poteva esportare né cancellare, contro il principio X della costituzione (minimizzazione).

## Decisione

- Una seconda rotta, `POST /api/v1/webhooks/stripe-connect/`, con il suo segreto (`STRIPE_CONNECT_WEBHOOK_SECRET`). Fa lo stesso lavoro della prima (controllo dell'indirizzo di provenienza, firma, salvataggio una volta sola, risposta subito, elaborazione in background): una classe base, e le due rotte dicono solo quale impostazione contiene il segreto. Un evento firmato per un endpoint non vale sull'altro.
- Un evento si **attribuisce a uno studio** dal campo `account`, mai da un dato scelto dal chiamante. Un evento di un conto che nessuno studio ha collegato, o con `livemode` vero, si conserva e si ignora. Un evento di un conto non può mai chiudere il tentativo di un altro conto.
- Il pagamento a cui si riferisce un rimborso o una contestazione si cerca per id del pagamento Stripe **e** per conto: nemmeno con un id esistente altrove si tocca il pagamento di un altro studio.
- Si salva una versione **ripulita** dell'evento: una lista bianca di identificativi, stati, importi e riferimenti. Nomi, email, indirizzi, dati di carta e l'indirizzo della pagina di pagamento non entrano.
- Ogni evento ha un **esito**: applicato, ignorato o "da controllare" (un rimborso senza pagamento, un importo diverso, un doppio pagamento, una valuta diversa). Lo studio vede gli ultimi venti "da controllare" con tipo e importo, mai il contenuto.
- Gli eventi già elaborati si **cancellano dopo 90 giorni**, ogni notte.
- Elaborazione con un piccolo registro di gestori per tipo di evento: ogni funzione ne aggiunge i suoi.

## Alternative scartate

- **Un solo endpoint con due segreti provati a turno**: meno chiaro, e ogni errore di firma diventerebbe ambiguo.
- **Continuare a salvare l'evento intero**: contro il principio X.
- **Cifrare l'evento intero**: i dati resterebbero comunque, e servirebbe una chiave in più da ruotare, per una cosa che non ci serve.
- **Non salvare gli eventi**: si perderebbe l'idempotenza (ADR-014) e la traccia di cosa è successo.

## Conseguenze

- La lista bianca è una scelta: se un domani servisse un altro campo, si aggiunge lì, con un test che prova che i dati personali restano fuori (c'è un test con un evento pieno di nomi, email, indirizzi e carte).
- Un'anomalia scoperta dalla riconciliazione oraria (non da un evento) resta solo nel log: non ha un evento da mostrare allo studio.
- La forma degli eventi di rimborso e contestazione (`refund.created`, `refund.updated`, `charge.dispute.created`, `charge.dispute.closed`) è quella della documentazione di Stripe: **non ho catturato eventi veri**, perché serve un conto di prova che finisca l'attivazione. È il primo controllo da fare con il sandbox.
- L'endpoint va registrato su Stripe (tipo "Connected accounts") e il segreto messo nelle variabili del server: il runbook lo spiega.
