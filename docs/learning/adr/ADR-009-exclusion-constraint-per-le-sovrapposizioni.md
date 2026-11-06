# ADR-009: Niente lezioni sovrapposte, garantito da PostgreSQL

- Stato: accettato
- Data: 2026-11-06

## Contesto

Un insegnante non può fare due lezioni nello stesso momento, e un allievo non può essere in due lezioni insieme. Prima della fase 2 nessuno lo impediva. Un doppio clic o due persone che prenotano nello stesso istante creavano una sovrapposizione.

Un controllo nell'applicazione ("cerco lezioni sovrapposte, se non ce ne sono inserisco") ha una finestra di race condition: due richieste possono fare il controllo insieme, non trovare niente, e inserire entrambe.

## Decisione

- Due **ExclusionConstraint** di PostgreSQL sulla tabella delle lezioni: `lesson_no_teacher_overlap` e `lesson_no_student_overlap`. Ognuno dice: non possono esistere due righe con lo stesso insegnante (o allievo) e intervalli `tstzrange(start_time, end_time, '[)')` che si sovrappongono (`&&`).
- I vincoli sono **parziali**: valgono solo per le lezioni `scheduled` e `completed`. Le lezioni annullate o "no show" liberano lo spazio.
- L'intervallo è semiaperto `[)`: una lezione che finisce alle 10:45 non si sovrappone a una che inizia alle 10:45.
- Serve l'estensione `btree_gist`, per usare `=` sugli id dentro un indice GiST.
- **`end_time` è una colonna salvata.** La colonna `duration_minutes` è stata eliminata. L'API continua a ricevere e restituire `duration_minutes`, calcolato dal service.
- Il service traduce la violazione del vincolo in una risposta **409 Conflict** con codice `lesson_overlap`, riconoscendo il vincolo dal nome.
- In caso di **deadlock** tra due inserimenti concorrenti (codice 40P01), il service riprova la scrittura fino a due volte. Al secondo tentativo vede la riga dell'altro e riceve una violazione normale, quindi un 409.

## Perché `end_time` salvato

Ho provato a mettere nel vincolo l'espressione `tstzrange(start, start + durata)`. PostgreSQL 16 la rifiuta: "functions in index expression must be marked IMMUTABLE". Sommare un intervallo a un `timestamptz` è una funzione STABLE, perché il risultato dipende dal fuso orario della sessione. Quindi l'unica strada è salvare la fine.

## Alternative scartate

- **Controllo solo nell'applicazione**: race condition.
- **Controllo più lock sulla riga dell'insegnante**: serializza le prenotazioni dello stesso insegnante, ma per la regola sull'allievo bisognerebbe bloccare due righe in un ordine fisso. Più complesso e più fragile.
- **Isolamento SERIALIZABLE**: funziona, ma impone di gestire i retry su tutte le transazioni.
- **Vincolo unico sull'orario di inizio**: funziona solo con slot fissi, non con durate libere.
- **Tenere sia `duration_minutes` sia `end_time`**: due fonti di verità che possono divergere.

## Conseguenze

- Nessuna richiesta, concorrente o no, può creare una sovrapposizione. Un test con due thread lo verifica.
- La migrazione fallisce se nel database esistono già sovrapposizioni, senza modificare niente. Lo abbiamo visto davvero sul database locale con i dati di benchmark.
- L'utente del database deve poter fare `CREATE EXTENSION`.
- Durante lo sviluppo i test hanno trovato un bug di fuso orario: la fine veniva calcolata sull'ora "da orologio" di Roma. Ora il calcolo avviene in UTC. Vedi `docs/knowledge-base/fine-lezione-e-ora-legale.md`.
