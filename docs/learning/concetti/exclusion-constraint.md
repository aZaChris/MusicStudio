# ExclusionConstraint: niente sovrapposizioni, garantito dal database

## TL;DR

Un ExclusionConstraint è un vincolo di PostgreSQL che vieta a due righe di "scontrarsi" secondo una regola che scegli tu. In MusicStudio lo usiamo per vietare due lezioni sovrapposte dello stesso insegnante o dello stesso allievo. A differenza di un controllo nel codice, funziona anche quando due richieste arrivano nello stesso istante. Il prezzo: una colonna in più, un'estensione di PostgreSQL e la gestione dei deadlock.

## Il problema reale

Un insegnante ha una lezione dalle 10:00 alle 10:45. Qualcuno ne prenota un'altra dalle 10:30. Il sistema deve dire no.

Il modo più intuitivo è nel codice: "prima di salvare, cerco se ci sono lezioni sovrapposte; se non ce ne sono, salvo". Funziona finché le richieste arrivano una alla volta. Ma immagina due richieste quasi simultanee, per esempio un doppio clic o due segretarie che prenotano lo stesso orario. La richiesta A controlla: niente sovrapposizioni. La richiesta B controlla: niente sovrapposizioni, perché A non ha ancora salvato. A salva. B salva. Risultato: due lezioni nello stesso momento.

Questo si chiama race condition: il risultato dipende da chi arriva prima, in un intervallo di pochi millisecondi. Nei test normali non si vede mai. In produzione succede, prima o poi.

## Come funziona

Pensa a una sala riunioni con un registro delle prenotazioni. Se chiunque può guardare il registro e poi scriverci sopra, due persone possono leggere "libero" e scrivere insieme. Se invece il registro è tenuto da un custode, che accetta una prenotazione solo dopo aver verificato che non si scontra con quelle già scritte, una alla volta, il problema sparisce. L'ExclusionConstraint è il custode, dentro il database.

Un vincolo `UNIQUE` dice: "non possono esistere due righe con lo stesso valore". Un ExclusionConstraint generalizza l'idea: "non possono esistere due righe per cui **tutti** questi confronti sono veri". Ogni confronto ha un operatore. Per noi:

- stesso insegnante, con l'operatore `=`;
- intervalli di tempo che si sovrappongono, con l'operatore `&&`.

Se una nuova riga avrebbe entrambe le condizioni vere con una riga esistente, PostgreSQL la rifiuta.

L'intervallo di tempo è un tipo range di PostgreSQL: `tstzrange(inizio, fine, '[)')`. La notazione `[)` significa "inizio incluso, fine esclusa". Così una lezione che finisce alle 10:45 non si scontra con una che inizia alle 10:45.

Il vincolo usa un indice GiST, una struttura adatta a forme e intervalli. Per mettere nello stesso indice anche il confronto `=` su un numero (l'id dell'insegnante) serve l'estensione `btree_gist`.

Infine, il vincolo può essere **parziale**, con una condizione `WHERE`: vale solo per alcune righe. Per noi solo le lezioni programmate o completate occupano lo spazio.

## Come lo abbiamo applicato in MusicStudio

Il modello è in `backend/apps/lessons/models.py`:

```python
ExclusionConstraint(
    name="lesson_no_teacher_overlap",
    expressions=[
        (TsTzRange("start_time", "end_time", RangeBoundary()), RangeOperators.OVERLAPS),
        ("teacher", RangeOperators.EQUAL),
    ],
    condition=models.Q(status__in=ACTIVE_STATUSES),
),
```

Ce n'è un secondo uguale per l'allievo, `lesson_no_student_overlap`. Nel database, la definizione reale è:

```text
EXCLUDE USING gist (tstzrange(start_time, end_time, '[)') WITH &&, teacher_id WITH =)
WHERE (status = ANY (ARRAY['scheduled', 'completed']))
```

**Il prima e dopo della durata.** Prima la lezione aveva `start_time` e `duration_minutes`. Ho provato a scrivere il vincolo su `tstzrange(start, start + durata)`. PostgreSQL 16 lo rifiuta: "functions in index expression must be marked IMMUTABLE". Sommare un intervallo a un `timestamptz` dipende dal fuso orario della sessione, quindi non è "immutabile", e non può stare in un indice. Ora salviamo `end_time`. L'API continua ad accettare e restituire `duration_minutes`: il service calcola la fine.

**La traduzione in 409.** Il service in `backend/apps/lessons/services.py` esegue la scrittura in un savepoint. Se PostgreSQL solleva una violazione, legge il nome del vincolo e risponde 409 Conflict con il codice `lesson_overlap` e un messaggio che dice se il problema è l'insegnante o l'allievo.

**Il deadlock scoperto dal test di concorrenza.** In `backend/apps/lessons/tests/test_overlap_concurrency.py` due thread, ognuno con la sua connessione, prenotano lo stesso orario nello stesso istante. La prima esecuzione è fallita con "deadlock detected". Cosa succede: ogni transazione inserisce la sua riga e poi, controllando il vincolo, trova la riga non ancora confermata dell'altra e aspetta. Si aspettano a vicenda, e PostgreSQL ne interrompe una. La soluzione è riprovare la scrittura persa: al secondo tentativo la riga dell'altra è confermata, e il vincolo dà una violazione normale. Ora il test passa sempre: una richiesta riceve 201, l'altra 409.

**La migrazione che si ferma.** Sul database locale c'erano ancora 200.000 lezioni casuali, usate per il benchmark degli indici. Applicando la migrazione, PostgreSQL ha rifiutato di creare il vincolo e ha mostrato le due righe in conflitto. Nessun dato è stato modificato. È il comportamento voluto: meglio fermarsi che "aggiustare" dati di clienti senza dirlo.

## Alternative considerate

**Controllo nel codice con un lock.** Bloccare la riga dell'insegnante con `select_for_update` prima di controllare. Funziona per l'insegnante, ma per l'allievo bisognerebbe bloccare anche la sua riga, sempre nello stesso ordine per evitare deadlock. Più codice, più punti fragili.

**Isolamento SERIALIZABLE.** PostgreSQL rileva i conflitti e annulla una transazione. Ma bisogna gestire i retry su tutte le scritture del progetto.

**Slot fissi con vincolo UNIQUE.** Se le lezioni iniziassero solo a orari fissi, un `UNIQUE (teacher, start_time)` basterebbe. Ma le durate sono libere.

## Errori comuni e trade-off

- **Dimenticare il vincolo parziale.** Senza `WHERE`, anche una lezione annullata bloccherebbe l'orario.
- **Intervallo chiuso `[]`.** Due lezioni consecutive risulterebbero sovrapposte.
- **Aritmetica dei fusi orari in Python.** Sommare minuti a un datetime con il fuso di Roma lavora sull'orologio locale. La notte del cambio dell'ora una lezione di 60 minuti durava due ore. Il calcolo ora si fa in UTC. Un test copre esattamente quel caso.
- **Non gestire i deadlock.** Con inserimenti concorrenti, un'eccezione inattesa diventerebbe un errore 500.
- **Trade-off:** serve un utente del database che possa creare l'estensione. In alcuni servizi gestiti non è scontato.

## Come lo spiegheresti a un colloquio

Per vietare lezioni sovrapposte ho usato un ExclusionConstraint di PostgreSQL invece di un controllo nel codice, perché il controllo nel codice ha una race condition tra la lettura e la scrittura. Il vincolo dice che non possono esistere due lezioni attive dello stesso insegnante con intervalli `tstzrange` che si sovrappongono, e ce n'è uno uguale per l'allievo. Ho dovuto salvare la fine della lezione, perché `timestamptz + interval` non è immutabile e non può stare in un indice. Il service traduce la violazione in un 409, e riprova in caso di deadlock, che si verifica davvero con due inserimenti simultanei. Un test con due thread dimostra che esattamente una prenotazione su due riesce.

## Domande di autoverifica

1. **Perché un controllo nel codice non basta?**
   Perché tra la lettura e la scrittura c'è una finestra in cui un'altra richiesta può fare lo stesso controllo e inserire anche lei.

2. **Cosa significa `[)` in `tstzrange`?**
   Inizio incluso e fine esclusa. Così due lezioni consecutive, una che finisce e l'altra che inizia alla stessa ora, non si sovrappongono.

3. **A cosa serve `btree_gist`?**
   A usare l'operatore `=` su colonne normali, come l'id dell'insegnante, dentro un indice GiST insieme agli intervalli.

4. **Perché abbiamo dovuto salvare `end_time`?**
   Perché `timestamptz + interval` è STABLE e non IMMUTABLE: dipende dal fuso orario. PostgreSQL non accetta funzioni non immutabili nelle espressioni di un indice.

5. **Perché due inserimenti simultanei possono andare in deadlock, e come lo gestiamo?**
   Ognuno inserisce la sua riga e poi aspetta la conferma dell'altro per controllare il vincolo. PostgreSQL interrompe uno dei due. Il service riprova, e al secondo tentativo riceve la violazione normale, quindi un 409.
