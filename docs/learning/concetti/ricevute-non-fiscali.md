# Ricevute non fiscali e numerazione senza buchi

## TL;DR

Una ricevuta è la prova che un pagamento è stato registrato, non un documento fiscale, e deve dirlo chiaramente. Il numero è unico per studio e anno e non ha buchi nemmeno quando venti ricevute nascono insieme: si ottiene bloccando la riga dello studio e prendendo il massimo più uno. Il PDF si genera ogni volta dai dati attuali, quindi una cancellazione GDPR non lascia nomi in giro.

## Il problema reale

I genitori vogliono una prova del pagamento. Lo studio vuole darla senza trasformarsi in un emittente di documenti fiscali, che sono un'altra faccenda, con obblighi veri. Quindi la ricevuta deve avere pochi dati, essere ben distinguibile da una fattura e portare un numero progressivo.

Quel numero è la parte difficile. Due ricevute dello stesso studio non possono avere lo stesso numero. E se una transazione fallisce a metà non deve restare un numero saltato. Con due richieste insieme, un semplice "leggi l'ultimo numero e aggiungi uno" le fa leggere entrambe lo stesso valore.

## Come funziona

È un blocchetto di ricevute numerate, uno per studio. Per staccarne una devi avere in mano il blocchetto: se qualcun altro lo sta usando, aspetti. Appena finisce, tocca a te. Non si possono staccare due ricevute con lo stesso numero, e se strappi un foglio prima di finire, non l'hai usato.

Il blocchetto, in un database, è un lock sulla riga dello studio. Chi lo ottiene legge il massimo numero dell'anno, scrive il successivo e finisce la transazione.

## Come lo abbiamo applicato in MusicStudio

**Una ricevuta per pagamento.** In `backend/apps/payments/models.py` il modello `Receipt` ha un collegamento uno-a-uno col pagamento, lo studio, l'anno, la sequenza, la lingua e chi l'ha emessa. Il numero (`2026-0007`) si compone al momento. Un vincolo di unicità su studio, anno e sequenza è la rete di sicurezza.

**L'emissione.** `issue_receipt` in `services.py`, in sintesi:

```python
with transaction.atomic():
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    # solo un pagamento "paid"; se la ricevuta esiste, si restituisce quella
    studio = Studio.objects.select_for_update().get(pk=payment.student.studio_id)
    year = timezone.localdate().year
    last = Receipt.objects.filter(studio=studio, year=year).aggregate(last=Max("sequence"))
    Receipt.objects.create(..., year=year, sequence=(last["last"] or 0) + 1)
```

Si usa il **massimo** e non il conteggio, così i numeri restano unici anche se le ricevute vecchie sparissero con la conservazione. Il lock sul pagamento fa sì che due richieste per lo stesso pagamento diano una sola ricevuta.

**La prova.** `test_receipt_concurrency.py` lancia venti thread veri su venti pagamenti dello stesso studio, fermi su una barriera e liberati insieme. Il risultato: venti numeri distinti, dall'1 al 20, nessuno saltato, nessuno ripetuto. Un secondo test manda sei richieste per lo stesso pagamento: una ricevuta, cinque risposte "già esistente".

**L'anno è locale.** Il 31 dicembre alle 23:30 UTC in Italia è già il primo gennaio. Un test lo verifica: il numero è `2027-0001`.

**Il PDF si genera al volo.** Si salvano il numero, la lingua e chi l'ha emessa, non il file. Il documento contiene solo studio, studente, importo, data, metodo e numero, più la frase "non è un documento fiscale" in italiano o inglese. Con reportlab e il flag `invariant`, a parità di dati escono gli stessi byte: un test lo verifica.

**Se il pagamento viene stornato.** La ricevuta tiene il suo numero e il PDF porta in alto il segno "ANNULLATA" e una scritta in diagonale su tutta la pagina. Una ricevuta non si emette per uno storno né per un pagamento in sospeso: la risposta è 409.

**Privacy.** Non salvare il PDF e non copiare i nomi è una scelta: dopo la richiesta di cancellazione di una famiglia, la ricevuta mostra l'etichetta anonima ("Allievo cancellato #N") e conserva importo, data e numero. Il prezzo: se lo studio o lo studente cambiano nome, la prossima generazione mostra il nome nuovo. Lo abbiamo accettato.

**Chi vede cosa.** L'insegnante e il titolare vedono le ricevute del proprio ambito; il genitore e lo studente adulto solo quelle dei propri figli. Un id fuori ambito dà 404.

**Misura vera.** Venti ricevute emesse una dopo l'altra, su questo portatile e senza rete, hanno impiegato 809 ms, con i numeri da `2026-0001` a `2026-0020`. La prova della concorrenza è il test con i thread, non questo tempo.

## Alternative considerate

- **Una sequenza PostgreSQL per studio**: lascia buchi quando la transazione annulla, e richiede un oggetto per ogni studio.
- **Un contatore in una tabella**: un'altra tabella per ciò che un lock già fa.
- **WeasyPrint**: richiede librerie di sistema nell'immagine.
- **Salvare il PDF**: conserverebbe nomi che una cancellazione dovrebbe far sparire.

## Errori comuni e trade-off

- Usare il conteggio al posto del massimo: i numeri si ripetono se qualcosa sparisce.
- Calcolare l'anno in UTC.
- Dimenticare la rete di sicurezza: un lock mal messo in un punto nuovo del codice non produrrebbe errori, solo numeri doppi. Il vincolo di unicità li farebbe fallire.
- Far sembrare la ricevuta una fattura. La frase "non è un documento fiscale" e il testo dei termini d'uso vanno fatti controllare da un professionista: non sono codice.
- Credere che un test in sequenza provi la concorrenza.

## Come lo spiegheresti a un colloquio

Il numero di una ricevuta si assegna bloccando la riga dello studio: chi arriva dopo aspetta, quindi i numeri sono distinti e senza buchi, e se la transazione annulla il numero non si consuma. Si prende il massimo più uno e non il conteggio, e un vincolo di unicità sta dietro al lock. Il PDF non si salva: si genera ogni volta dai dati attuali, così la cancellazione dei dati personali funziona. Ho provato la concorrenza con venti thread veri.

## Domande di autoverifica

1. **Perché un semplice "leggi l'ultimo e aggiungi uno" non basta?** Due richieste insieme leggono lo stesso valore. Serve il lock.
2. **Perché il massimo e non il conteggio?** Se le ricevute vecchie sparissero, il conteggio ripeterebbe numeri.
3. **Che anno finisce nel numero a mezzanotte di Capodanno in Italia?** Quello locale: alle 23:30 UTC del 31 dicembre è già il nuovo anno.
4. **Perché non si salva il PDF?** Conserverebbe nomi che una richiesta di cancellazione dovrebbe far sparire.
5. **Cosa succede alla ricevuta se il pagamento è stornato?** Tiene il numero e porta il segno "annullata".
