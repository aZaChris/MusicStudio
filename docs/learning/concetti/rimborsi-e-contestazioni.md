# Rimborsi e contestazioni: come tornano nel registro

## TL;DR

Se uno studio rimborsa un genitore, o perde una contestazione, il registro di cassa deve restare giusto. Succede su Stripe, non da noi. Stripe ci avvisa e noi aggiungiamo una **riga di storno** collegata al pagamento, senza mai modificarlo. Un pagamento può avere più storni, anche parziali, e la loro somma non supera mai l'importo.

## Il problema reale

Nella fase 8 il registro è diventato affidabile: un pagamento incassato non si riscrive. Se sbagli, fai uno **storno**, una riga nuova collegata alla prima. L'originale resta, così un mese già consegnato al commercialista non cambia.

Con il pagamento online c'è un caso nuovo. Il denaro è sul conto Stripe dello studio, e lo studio può rimborsare dalla sua pagina di Stripe. Può rimborsare tutto, o solo una parte, o fare due rimborsi in giorni diversi. Un genitore può anche contestare il pagamento con la sua banca (un chargeback), e Stripe può togliere il denaro allo studio.

Se il registro non lo sapesse, direbbe "incassato 100 euro" per denaro che lo studio non ha più. Il commercialista sbaglierebbe i conti.

## Come funziona, con un'analogia

Pensa a un quaderno di cassa scritto a penna. Non si cancella mai. Se un cliente ti restituisce un paio di scarpe, non cancelli la vendita: scrivi una riga nuova "reso, 30 euro, scarpe del 3 novembre". Il quaderno dice tutto. Se ti rendono solo un paio su due, scrivi un reso parziale. Se ne rendono due in tempi diversi, due righe.

Il nostro registro funziona così. Ogni riga di storno dice **perché** esiste: una correzione fatta a mano (`manual`), un rimborso (`refund`) o una contestazione persa (`dispute`).

## Come l'abbiamo applicato in MusicStudio

**Il modello.** `reversal_of` era una relazione uno-a-uno: un pagamento, al massimo uno storno. Ora è una chiave esterna. Le righe che vengono da Stripe hanno anche un `provider_ref`, l'id del rimborso o della contestazione, che è **unico**.

Due vincoli lo tengono in ordine. Lo storno manuale resta uno solo e per l'importo intero (un vincolo parziale: univoco dove la causa è `manual`). E un id di Stripe non può comparire due volte, quindi la stessa notifica ripetuta non scrive nulla.

**"Stornato" è una somma.** Una funzione sola calcola quanto è stato stornato, e un'altra dice se è stornato per intero. Tutto il resto del codice le usa: elenco pagamenti, stato dello studente, pacchetti da pagare, ricevute.

```python
def not_fully_reversed() -> Q:
    # un rimborso parziale lascia il pagamento "incassato"
    return Q(reversed_amount=0) | Q(reversed_amount__lt=F("amount"))
```

Un rimborso parziale abbassa il netto e lascia il pacchetto pagato: le lezioni ci sono state. Un rimborso totale riapre il pacchetto.

**La regola della somma.** Gli storni di un pagamento non possono superare il suo importo. Non è un vincolo che un database sa esprimere, quindi lo controlliamo nel codice, mentre teniamo bloccata la riga dell'originale:

```python
locked = Payment.objects.select_for_update().get(pk=original.pk)
already = Payment.objects.filter(reversal_of=locked).aggregate(total=Sum("amount"))["total"]
if (already or Decimal("0.00")) + amount > locked.amount:
    return None, "exceeds"
```

Se due rimborsi arrivano insieme, il secondo aspetta e poi vede la somma aggiornata. È lo stesso trucco dei numeri delle ricevute.

**Gli eventi.** Stripe manda `refund.created` e `refund.updated` per i rimborsi, `charge.dispute.created` e `charge.dispute.closed` per le contestazioni. Un rimborso conta solo con stato `succeeded` (uno in attesa non ha mosso denaro). Una contestazione aperta si segna sul pagamento; se è persa nasce lo storno, se è vinta non cambia nulla.

**Quale pagamento?** Si cerca per id del pagamento Stripe **e** per conto. Così un evento di uno studio non può toccare il pagamento di un altro, nemmeno con un id che esiste altrove.

**Quando qualcosa non torna.** Un rimborso che non corrisponde a nessun pagamento (fatto a mano, per esempio), o più grande di ciò che resta, non scrive nulla. Viene messo in una lista "da controllare" che il titolare vede nella pagina del conto, con il tipo e l'importo, mai i dati di chi ha pagato.

**La data.** Uno storno è datato **oggi**, mai a ritroso. Un rimborso di dicembre su un pagamento di novembre cade nel registro di dicembre. Novembre non cambia.

## Alternative considerate

Potevamo ignorare i rimborsi parziali e segnalarli e basta. Ma allora il registro mostrerebbe denaro che lo studio non ha più, e non è accettabile. Potevamo trattare un parziale come uno storno intero più un nuovo pagamento: ma inventerebbe un pagamento che non è mai avvenuto. Una tabella `Refund` a parte avrebbe dato ai totali due fonti da sommare. Un campo "importo rimborsato" sul pagamento avrebbe riscritto una riga definitiva.

## Errori comuni e trade-off

L'errore classico è contare i rimborsi dall'evento sbagliato. Con la vecchia API un rimborso si leggeva dentro l'oggetto del pagamento, ma nelle versioni recenti quell'elenco non c'è più: per questo usiamo gli eventi del rimborso.

Un altro errore è fidarsi dell'ordine: un rimborso può arrivare più volte, o prima in attesa e poi riuscito. L'id unico lo rende innocuo.

Il limite che va detto: la regola "somma ≤ importo" sta nel codice e non nel database. Un test, `test_final_guard.py`, legge il sorgente e fallisce se qualcuno crea righe di pagamento fuori dai service.

Un secondo limite: se una notifica si perde, lo storno non nasce da solo. Stripe riprova a consegnare per giorni, e rileggere un evento è sicuro. Non abbiamo un controllo periodico sui rimborsi.

E il rimborso lo fa lo studio sulla pagina di Stripe. Lo storno manuale dal registro continua a **non** restituire denaro: la schermata lo dice e rimanda a Stripe.

## Cosa è provato e cosa no

Provato con test: rimborso totale e parziale, due parziali che si sommano, un rimborso notificato più volte, un rimborso oltre il residuo, una contestazione aperta, persa e vinta, un evento di un altro studio, 6 thread con rimborsi insieme, uno storno manuale contro un rimborso, i totali con ogni tipo di storno. Gli eventi dei test hanno la forma indicata dalla documentazione di Stripe: **non ho catturato eventi veri**, perché serve un conto di prova attivato. È il primo controllo da fare sul sandbox.

## Come lo spiegheresti a un colloquio

Il registro di cassa non si riscrive mai: le correzioni sono righe nuove collegate all'originale. Quando ho aggiunto i rimborsi di Stripe ho dovuto passare da "un solo storno" a "più storni", per i rimborsi parziali. Ho reso "stornato" una somma calcolata in un solo posto, ho messo un id unico per ogni rimborso così le notifiche ripetute non fanno danni, e ho protetto la regola "mai oltre l'importo" con un blocco di riga, provato con thread veri. Un evento si attribuisce a uno studio solo tramite il suo conto, quindi non può toccare i dati di un altro. E dove qualcosa non torna, il sistema non indovina: lo mostra al titolare.

## Cinque domande di autoverifica

**1. Perché un rimborso non modifica il pagamento originale?**
Perché un pagamento incassato è definitivo: il registro si corregge solo con righe nuove, così un mese chiuso non cambia.

**2. Come si evita di scrivere due volte lo stesso rimborso?**
Ogni riga del fornitore ha un `provider_ref` unico (l'id del rimborso di Stripe): un duplicato viene rifiutato dal database.

**3. Un rimborso parziale riapre il pacchetto?**
No. Abbassa il netto, ma il pacchetto resta pagato. Lo riapre solo uno storno per intero.

**4. Perché serve un blocco di riga per la regola "somma ≤ importo"?**
Perché non si può esprimere come vincolo del database. Il blocco fa aspettare chi arriva secondo, che poi vede la somma aggiornata.

**5. Cosa succede a un rimborso che non corrisponde a nessun pagamento?**
Non cambia nulla nel registro. Compare nella lista "da controllare" del titolare, con tipo e importo.
