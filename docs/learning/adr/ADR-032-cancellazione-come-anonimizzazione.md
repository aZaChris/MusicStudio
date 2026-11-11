# ADR-032: Cancellazione come anonimizzazione e tempi di conservazione

- Stato: accettato
- Data: 2026-11-11

## Contesto

Un genitore ha il diritto di scaricare i dati suoi e dei suoi figli e di chiederne la cancellazione. Ma lo studio ha anche degli obblighi: deve conservare i pagamenti per la contabilità e per il fisco. Se cancellassimo tutto con un `DELETE` a cascata, distruggeremmo anche lo storico dei pagamenti dello studio e i suoi totali non tornerebbero più.

## Decisione

- **Esportare** significa un file JSON con l'account, i figli, le loro lezioni (note comprese, decifrate), i pacchetti, i pagamenti e i consensi. L'ambito lo decide il ruolo di chi chiede, mai un id nella richiesta: un genitore riceve solo i figli collegati a lui, uno studente adulto solo sé stesso.
- **Cancellare** significa *anonimizzare sul posto*. Nella stessa transazione:
  - l'account perde nome ed email (diventa `erased-<uuid>@invalid`), la password diventa inutilizzabile, le sessioni finiscono;
  - ogni figlio senza altri genitori collegati diventa "Allievo cancellato #id", senza strumento, archiviato, con le note delle lezioni svuotate;
  - lezioni, pacchetti e pagamenti restano con importi e date, ma senza nomi;
  - consensi, inviti all'indirizzo, dispositivo MFA e token vengono eliminati.
- Se un figlio ha **due genitori**, se ne va solo quello che chiede la cancellazione. Il figlio resta e l'insegnante riceve un'email che lo dice, senza nominare chi se n'è andato.
- Mentre c'è un **pagamento online aperto** per i figli, la cancellazione è rifiutata (409): chiudere l'account a metà di un pagamento lascerebbe soldi senza proprietario.
- Il **titolare** di uno studio può cancellarsi solo se lo studio è vuoto. Con allievi attivi, prima li si sposta o li si cancella.
- **Ritirare il consenso** equivale a cancellare i figli interessati dal lato di quel genitore.
- Ogni esportazione e cancellazione scrive nell'audit log.

Tempi di conservazione (applicati ogni giorno da un task, vedi T040): allievi archiviati anonimizzati dopo 24 mesi dall'ultima attività, pagamenti eliminati dopo 10 anni, voci di audit dopo 12 mesi, registrazioni mai confermate dopo 7 giorni.

## Alternative scartate

- **Cancellazione fisica a cascata**: pulita, ma distrugge lo storico dei pagamenti. Il totale incassato dallo studio cambierebbe retroattivamente.
- **Soft delete (un flag "cancellato")**: i dati personali resterebbero nel database. Non è cancellazione.
- **Export asincrono via email**: a questa scala (centinaia di righe per famiglia) una risposta sincrona basta ed è più semplice. Da rivedere se gli export crescono.

## Conseguenze

- Una cancellazione non si può annullare. Per questo serve la password e il testo dell'interfaccia deve dirlo chiaramente.
- Un test cerca nel database, colonna per colonna, nome ed email della persona cancellata: se un domani una nuova tabella conserva un dato personale, il test lo trova.
- Quali importi e per quanto tempo conservare sono scelte legali: il periodo di 10 anni è una bozza da far validare a un professionista (task del proprietario).
