# ADR-035: Ricevute non fiscali con numerazione senza buchi

- Stato: accettato
- Data: 2026-11-15

## Contesto

I genitori chiedono una prova del pagamento. MusicStudio non emette documenti fiscali: la ricevuta deve dirlo chiaramente. Ogni ricevuta ha un numero, e i numeri di uno studio devono essere distinti e senza buchi, anche se due ricevute nascono nello stesso momento.

## Decisione

- Una ricevuta per pagamento incassato (un vincolo uno-a-uno), solo per un pagamento `paid`: non per uno storno, non per uno in sospeso. Emettere due volte restituisce la stessa ricevuta, con lo stesso numero e la stessa lingua.
- Il numero è `AAAA-NNNN`, unico per studio e anno. L'emissione blocca la riga dello studio (`select_for_update`, come già fa lo spostamento di un insegnante), prende il **massimo** della sequenza dell'anno locale e aggiunge uno. Emissioni contemporanee dello stesso studio si mettono in coda. Se la transazione annulla, il numero non è consumato. Un vincolo di unicità su studio, anno e sequenza è la rete di sicurezza.
- L'anno è quello **locale** (Europe/Rome): alle 23:30 UTC del 31 dicembre in Italia è già il primo gennaio.
- Il PDF non si salva: si genera ogni volta dai dati attuali e dal numero e dalla lingua salvati. Contiene solo studio, studente, importo, data, metodo e numero, più la frase che non è un documento fiscale. Se il pagamento è stato stornato, la ricevuta tiene il suo numero e porta il segno "annullata".
- Il PDF è deterministico: stesso input, stessi byte (reportlab con `invariant`).

## Alternative scartate

- **Una sequenza PostgreSQL per studio**: lascia buchi quando una transazione annulla, e un oggetto per ogni studio da gestire.
- **Il conteggio al posto del massimo**: i numeri si ripeterebbero se le ricevute vecchie sparissero con la conservazione.
- **Un contatore in una tabella a parte**: un'altra tabella per ciò che un lock fa già.
- **Salvare il PDF o una copia dei nomi**: sopravvivrebbe a una richiesta di cancellazione. Con la generazione al volo, dopo l'anonimizzazione la ricevuta mostra l'etichetta anonima e conserva importo, data e numero.
- **WeasyPrint**: richiede librerie di sistema nell'immagine. Si è scelto reportlab, senza dipendenze di sistema.

## Conseguenze

- Se lo studio o lo studente cambiano nome, la prossima generazione mostra il nuovo nome: è accettato, e preferibile a un nome salvato per sempre.
- La frase "non è un documento fiscale" e il testo dei termini d'uso vanno fatti controllare da un professionista prima che gli studi ci facciano affidamento. Non fa parte del codice.
- `pillow` entra come dipendenza di reportlab.
