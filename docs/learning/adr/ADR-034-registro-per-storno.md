# ADR-034: Il registro di cassa si corregge per storno

- Stato: accettato
- Data: 2026-11-15

## Contesto

Fino alla fase 7 un pagamento si poteva modificare e cancellare in qualunque stato. Un errore di registrazione spariva senza lasciare traccia: né l'insegnante né il suo commercialista potevano sapere che l'errore era esistito. Un registro che si può riscrivere in silenzio non è affidabile.

Lo studio è autonomo: incassa e fa la contabilità per conto proprio. MusicStudio non muove né verifica denaro. Serve però un registro che sia una base onesta per chi poi fa i conti.

## Decisione

- Un pagamento **pagato** (o una riga di storno) è definitivo: nessuna modifica, nessuna cancellazione. I service rifiutano con `409 payment_final`.
- Si corregge con uno **storno**: una nuova riga di `Payment` con stato `reversal`, collegata all'originale da `reversal_of`, una relazione uno-a-uno. Ripete importo e metodo, è datata nel giorno in cui si fa, porta chi, quando e perché (il motivo è testo libero, quindi cifrato).
- L'originale **non viene mai riscritto**. "Stornato" non è uno stato salvato: si ricava dall'esistenza dello storno. Per questo un mese già consegnato non cambia: l'incassato di novembre conta ancora l'originale, lo stornato di dicembre conta lo storno.
- "Al massimo uno storno" e "due richieste insieme, uno solo" li garantisce il database: il collegamento uno-a-uno è univoco, e un vincolo di controllo dice che lo storno ha sempre il collegamento e solo lo storno lo ha. Il service blocca anche la riga dell'originale, così chi arriva secondo riceve un 409 pulito.
- I pagamenti in sospeso e scaduti restano modificabili e cancellabili, perché sono attese e non denaro incassato. La cancellazione lascia una voce nel registro delle azioni.
- Pacchetto pagato significa: ha un pagamento pagato e non stornato. La stessa regola vale per il checkout, per lo stato dello studente e per i pacchetti ancora da pagare.

## Alternative scartate

- **Segnare l'originale come stornato e aggiungere una contropartita**: riscrive la storia e sposta i totali di un mese chiuso.
- **Importi negativi sullo storno**: il segno è già nello stato. Un importo sempre positivo si controlla con un vincolo semplice.
- **Una tabella `Reversal` separata**: ogni lista e ogni totale dovrebbe interrogare due posti.
- **Soft delete**: nasconde l'errore invece di mostrare la correzione.
- **Un trigger nel database che vieta l'update**: aggiunge migrazioni e operazioni per poco guadagno, in un prodotto con un solo codice.

## Conseguenze

- Il limite è dichiarato: `QuerySet.update()` e `QuerySet.delete()` non passano dai metodi dei modelli, quindi chi scrivesse un aggiornamento di massa potrebbe aggirare la regola. Un test (`test_final_guard.py`) legge il codice e fallisce se un posto nuovo scrive in blocco sui pagamenti.
- L'unica eccezione voluta è il job di conservazione, che cancella in blocco i pagamenti oltre i dieci anni. Per questo il collegamento allo storno ha `CASCADE` e non `PROTECT`: uno storno recente di un pagamento molto vecchio non deve bloccare il job.
- Contratto API: update e delete di un pagamento pagato ora rispondono 409. L'app web e l'app mobile non li chiamano (letto dal codice, non provato eseguendo l'app). Lo stato `reversal` è un valore nuovo dell'elenco: i client che fanno un conto "non pagato = da incassare" lo contano male, e la nota per l'app mobile lo segnala.
- Lo storno di un pagamento con carta corregge il registro e non rimborsa nulla: lo dice la risposta (`refund: false`) e lo dice la schermata.
