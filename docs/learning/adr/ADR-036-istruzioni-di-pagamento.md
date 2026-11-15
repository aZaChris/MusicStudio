# ADR-036: Istruzioni di pagamento dello studio, senza verifica bancaria

- Stato: accettato
- Data: 2026-11-15

## Contesto

Gli insegnanti ricevono sempre la stessa domanda dai genitori: dove mando i soldi? MusicStudio non muove denaro e non legge conti bancari. Può però mostrare ai genitori come lo studio vuole essere pagato, e l'insegnante segna poi il pagamento come ricevuto.

## Decisione

- Un solo insieme di istruzioni per studio: intestatario, IBAN, banca facoltativa, nota facoltativa (per esempio cosa scrivere nella causale) e fino a cinque link esterni (etichetta e indirizzo `https`).
- Le modifica solo il titolare; gli insegnanti leggono. Lo studio viene sempre dal contesto di chi chiama, mai da un id nella richiesta: non c'è un id da forzare.
- **Intestatario e IBAN sono cifrati a riposo** (lo stesso campo cifrato delle note delle lezioni). Non compaiono nei log, né nei report di errore (il corpo delle richieste a `/payment-instructions/` è nell'elenco dei percorsi sensibili di Sentry), né nel registro delle azioni, che riceve solo i nomi dei campi cambiati.
- L'IBAN si controlla con formato e checksum mod-97, con la sola libreria standard. Non si controlla che il conto esista: nessuna banca viene interrogata, e la schermata lo dice ("MusicStudio non controlla nessuna banca").
- Un solo endpoint per le famiglie, `payment-instructions/open/`: una voce per ogni studio in cui hanno un pacchetto ancora da pagare, con gli id degli studenti che lo hanno. Tre query, qualunque sia il numero di pacchetti. Il portale mostra le istruzioni accanto al pacchetto del figlio che deve pagare e a nessun fratello che non deve nulla.
- L'esportazione dei dati del titolare le include, e la cancellazione del suo account le toglie.

## Alternative scartate

- **Istruzioni dentro ogni pacchetto**: ripetute, e una query per pacchetto.
- **Istruzioni per insegnante**: fuori dal perimetro. Un insegnante che lavora da solo è il titolare del proprio studio.
- **IBAN in chiaro**: è un dato che un attaccante userebbe per frodi e che il titolare si aspetta protetto.
- **Una libreria per l'IBAN**: una dipendenza per quindici righe e un test con numeri noti.
- **Link inseriti senza controllo**: un `javascript:` o un `http` non deve mai arrivare a un genitore.

## Conseguenze

- I dati bancari sono visibili in chiaro al titolare e agli insegnanti dello studio, e ai genitori che devono pagare: è lo scopo. Chi ha accesso al database e alla chiave di cifratura può leggerli.
- Se uno studio non salva nulla, il portale non mostra nulla e nulla si rompe.
- Il test dei log invia un IBAN attraverso una richiesta rifiutata e una che manda in errore il server, e non lo trova in nessun log, voce di audit o evento Sentry.
