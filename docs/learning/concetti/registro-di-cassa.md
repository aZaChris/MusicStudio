# Registro di cassa: correggere senza cancellare

## TL;DR

Un registro di cassa è affidabile solo se non si può riscrivere in silenzio. In MusicStudio un pagamento pagato non si modifica e non si cancella: un errore si corregge con uno storno, una nuova riga collegata all'originale che dice chi, quando e perché. L'originale resta visibile e un mese già consegnato al commercialista non cambia. I totali si calcolano con una sola query SQL, e l'esportazione in CSV neutralizza le formule.

## Il problema reale

Un'insegnante registra 40 euro in contanti sullo studente sbagliato. Fino alla fase 7 poteva aprire il pagamento, cambiare lo studente e salvare. Oppure cancellarlo. In entrambi i casi dell'errore non restava nulla. Se il commercialista aveva già ricevuto il riepilogo di novembre, i conti non tornavano più e nessuno sapeva perché.

C'è un secondo problema, più sottile. Un totale mensile calcolato su righe che possono cambiare è un totale che può cambiare. "Quanto ho incassato a novembre?" deve avere la stessa risposta a dicembre, anche se a dicembre si è scoperto un errore.

MusicStudio non muove denaro e non fa fatture. Ma il registro dei pagamenti è la base su cui lo studio fa la propria contabilità, e deve essere onesto.

## Come funziona

È un quaderno scritto a penna. Se sbagli, non usi la gomma e non strappi la pagina: scrivi una riga nuova che dice "annullo la riga di prima, per questo motivo", con la data di oggi. Chi legge vede l'errore, la correzione e quando è stata fatta. Poi scrivi la riga giusta.

Ne seguono tre regole.

- **L'originale non si tocca mai.** Nemmeno per segnarlo come "stornato": quella informazione si ricava dall'esistenza dello storno.
- **Lo storno ha la data di oggi, mai a ritroso.** Un periodo già consegnato non cambia.
- **Si storna una volta sola.** Per rimettere il pagamento si registra un pagamento nuovo.

## Come lo abbiamo applicato in MusicStudio

**Lo storno è una riga di `Payment`.** In `backend/apps/payments/models.py` il pagamento ha uno stato in più, `reversal`, e un collegamento all'originale:

```python
reversal_of = models.OneToOneField(
    "self", on_delete=models.CASCADE, null=True, blank=True, related_name="reversal"
)
```

Essere uno-a-uno vuol dire che il database stesso rifiuta un secondo storno sullo stesso pagamento. Due vincoli di controllo completano il quadro: uno storno ha sempre il collegamento, e solo lo storno lo ha; e uno storno ha un importo positivo.

**Il service.** `reverse_payment` in `services.py` blocca la riga dell'originale con `select_for_update`, rifiuta tutto ciò che non è pagato, già stornato o uno storno a sua volta, crea la riga di storno con la data locale di oggi e scrive la voce di audit, senza il testo del motivo. Se due richieste arrivano insieme, la seconda aspetta il lock e poi riceve un 409 `already_reversed`.

**La prova che regge.** `test_reversal_concurrency.py` lancia dei thread veri, ciascuno con la sua connessione, fermati da una barriera e liberati insieme. Con 2 e con 6 thread contemporanei il risultato è sempre una riga di storno e tutti gli altri 409.

**"Definitivo" nei service.** `update_payment` e `delete_payment` chiamano `ensure_not_final`: su un pagamento pagato o su uno storno rispondono `409 payment_final`. Il limite è dichiarato nell'ADR-034: `QuerySet.update()` e `QuerySet.delete()` non passano dai metodi del modello. Un test, `test_final_guard.py`, legge il codice e fallisce se un posto nuovo scrive in blocco su `Payment`. Oggi ce n'è uno solo, voluto: il job che cancella i pagamenti oltre i dieci anni.

**I totali.** Una sola query con somme condizionali, raggruppata per metodo:

```python
.values("method").annotate(
    received=Sum("amount", filter=Q(status=Payment.Status.PAID)),
    reversed=Sum("amount", filter=Q(status=Payment.Status.REVERSAL)),
)
```

L'incassato è la somma dei pagamenti pagati per la loro data. Lo stornato è la somma degli storni per la *loro* data. Il netto è la differenza. Un pagamento di novembre stornato il 3 dicembre conta in novembre come incassato e in dicembre come stornato. Un test lo verifica con un calcolo fatto a mano: novembre 250,00 incassati, 100,00 stornati, 150,00 netti.

**Date locali.** Le giornate e i mesi si calcolano in ora italiana, non UTC. Il test sul cambio di giorno usa le 23:30 UTC del 30 novembre, che in Italia sono già le 00:30 del primo dicembre: lo storno cade in dicembre.

**L'esportazione.** Il CSV usa il punto e virgola, UTF-8 con BOM e fine riga `\r\n`, perché Excel con impostazioni italiane spezza le colonne sul punto e virgola e ha bisogno del BOM per le lettere accentate. È una scelta discutibile: altrove il separatore è la virgola. I testi scritti da una persona (studente, motivo) vengono neutralizzati: se iniziano con `=`, `+`, `-` o `@`, si aggiunge un apostrofo davanti, così il foglio di calcolo li mostra come testo. Gli importi non si toccano, perché un `-40.00` legittimo è un numero.

**Misure vere.** Su questo portatile, in-process e senza rete: il riepilogo di un mese con 2.000 voci ha impiegato 22 ms (mediana di cinque prove; la primissima chiamata, a freddo, 874 ms). L'esportazione CSV di un anno con 5.000 righe ha impiegato 629 ms. Non dicono nulla su un server sotto carico.

## Alternative considerate

- **Segnare l'originale come stornato**: riscrive la storia e sposta i totali.
- **Importi negativi**: il segno è già nello stato.
- **Un trigger che vieta l'update**: più migrazioni e più operazioni per poco guadagno.
- **Soft delete**: nasconde l'errore invece di mostrare la correzione.

## Errori comuni e trade-off

- Contare come "da incassare" tutto ciò che non è pagato: uno storno risulterebbe da incassare. Era la riga di codice sia nel portale web sia nell'app mobile.
- Calcolare i mesi in UTC: un pagamento delle 23:30 finisce nel giorno sbagliato.
- Pensare che il database sia protetto da ogni scrittura: gli aggiornamenti di massa aggirano i metodi del modello.
- Neutralizzare anche i numeri: il CSV non sarebbe più leggibile come numeri.
- Fidarsi di un test di concorrenza che non usa thread veri: due richieste in sequenza non provano nulla.

## Come lo spiegheresti a un colloquio

Un registro di cassa non si riscrive: si corregge per storno. Lo storno è una riga nuova, collegata uno-a-uno all'originale, quindi il database garantisce che avvenga una volta sola anche con due richieste insieme. L'originale non viene mai modificato, così i totali di un mese chiuso non cambiano. Il netto di un periodo è una sola query con somme condizionali. Il limite è dichiarato: gli aggiornamenti di massa aggirano le regole del modello, e un test fa da guardia.

## Domande di autoverifica

1. **Perché l'originale non si marca come "stornato"?** Perché riscriverlo sposterebbe i totali di un mese chiuso. Lo stato si ricava dall'esistenza dello storno.
2. **Chi garantisce che due insegnanti non stornino lo stesso pagamento?** Il collegamento uno-a-uno è univoco nel database, e il service blocca la riga dell'originale.
3. **In quale mese cade uno storno fatto il 3 dicembre su un pagamento di novembre?** In dicembre, come stornato. Novembre conta ancora l'originale.
4. **Cosa impedisce un `Payment.objects.update(...)` che aggira la regola?** Il database no. Un test legge il codice e fallisce se compare un posto nuovo.
5. **Perché neutralizzare i campi di testo nel CSV?** Un nome che inizia con `=` potrebbe essere eseguito come formula da un foglio di calcolo. Si aggiunge un apostrofo.
