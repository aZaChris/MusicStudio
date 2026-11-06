# Indici ed EXPLAIN in PostgreSQL

## TL;DR

Un indice è una struttura che permette a PostgreSQL di trovare le righe senza leggere tutta la tabella. `EXPLAIN ANALYZE` mostra come il database esegue davvero una query. In MusicStudio abbiamo aggiunto indici composti e parziali per le query più frequenti, e cambiato un filtro sulle date che impediva di usarli bene. Con 200.000 lezioni, la query della settimana è passata da 1.000 a 20 blocchi letti.

## Il problema reale

Con pochi dati ogni query è veloce. Il database legge tutta la tabella e nessuno se ne accorge. Il problema arriva quando i dati crescono. Una tabella di lezioni accumula righe ogni settimana, per ogni insegnante, per sempre. Le query che filtrano per "lezioni di questo insegnante in questa settimana" diventano più lente, e non perché il codice sia cambiato.

Django crea da solo un indice su ogni foreign key. È un buon inizio, ma non basta. Se la query filtra per insegnante **e** per data, l'indice sul solo insegnante trova tutte le lezioni di quell'insegnante, magari mille, e poi deve scartarle una per una.

C'è anche un errore più sottile: scrivere il filtro in un modo che impedisce all'indice di funzionare.

## Come funziona

Pensa all'indice analitico in fondo a un libro. Se cerchi "PostgreSQL", non leggi tutte le pagine: guardi l'indice, trovi i numeri di pagina e vai lì. L'indice B-tree di un database è la stessa cosa, ordinata in modo da trovare un valore o un intervallo in pochi passi.

**Indice composto.** Un indice su più colonne, per esempio `(teacher_id, start_time)`. È ordinato prima per insegnante, poi per data. Una query "insegnante 8, date tra lunedì e domenica" va dritta al punto giusto e legge solo le righe che servono. L'ordine delle colonne conta: lo stesso indice non aiuta una query che filtra solo per data.

**Indice parziale.** Un indice che contiene solo alcune righe, quelle che rispettano una condizione. Per esempio solo le lezioni programmate e non ancora ricordate. È piccolo, quindi veloce e economico da mantenere.

**EXPLAIN ANALYZE.** Chiedi al database il piano di esecuzione e lo fai eseguire davvero. Vedi se usa un indice ("Index Scan", "Bitmap Index Scan") o legge tutta la tabella ("Seq Scan"), quante righe scarta ("Rows Removed by Filter"), quanti blocchi legge e quanto tempo impiega. In Django si ottiene con `queryset.explain(analyze=True)`.

## Come lo abbiamo applicato in MusicStudio

Gli indici sono dichiarati nel `Meta.indexes` dei modelli e creati da migrazioni:

- `Lesson (teacher, start_time)`: agenda settimanale, prossime lezioni, dashboard.
- `Lesson (start_time)` parziale, `WHERE status = 'scheduled' AND reminder_sent_at IS NULL`: lo sweep dei promemoria.
- `Payment (student, -date)`: ultimo pagamento di ogni allievo.
- `Payment (status)`: conteggio dei pagamenti in attesa.
- `Package (student, -purchase_date)` parziale, `WHERE lessons_remaining > 0`: pacchetto attivo.

Si trovano in `backend/apps/lessons/models.py`, `backend/apps/payments/models.py` e `backend/apps/packages/models.py`. Le migrazioni sono `backend/apps/lessons/migrations/0003_lesson_indexes.py` e simili.

**Il prima e dopo del filtro sulle date.** Il codice originale filtrava la settimana così: `start_time__date__gte=lunedì`. Sembra naturale. Ma `__date` diventa in SQL una conversione di fuso orario e un cast a data sulla colonna. Una funzione applicata alla colonna impedisce a PostgreSQL di usare l'indice su quella colonna. Ora `week_bounds` in `backend/apps/lessons/selectors.py` calcola due datetime con fuso orario, lunedì alle 00:00 e il lunedì dopo, e filtra con un intervallo sulla colonna nuda.

Ho misurato con 200.000 lezioni, 200 insegnanti e circa 1.000 lezioni per insegnante, nel PostgreSQL 16 locale.

Con il filtro `__date` (il vecchio modo):

```text
Bitmap Heap Scan on lessons_lesson  (actual time=1.329..3.148 rows=20)
  Recheck Cond: (teacher_id = 8)
  Filter: ((start_time AT TIME ZONE 'Europe/Rome')::date >= '2026-11-02' ...)
  Rows Removed by Filter: 980
  Heap Blocks: exact=1000
  ->  Bitmap Index Scan on lessons_lesson_teacher_id_57e59f26
Execution Time: 3.199 ms
```

Con l'intervallo sulla colonna e l'indice composto:

```text
Bitmap Heap Scan on lessons_lesson  (actual time=1.204..1.245 rows=20)
  Heap Blocks: exact=20
  ->  Bitmap Index Scan on lesson_teacher_start_idx
        Index Cond: ((teacher_id = 8) AND (start_time >= ...) AND (start_time < ...))
Execution Time: 1.374 ms
```

La differenza importante non è il tempo, che con dati in cache è piccolo. È il lavoro: 1.000 blocchi letti e 980 righe scartate contro 20 blocchi e zero scarti. Con più storia per insegnante il primo cresce, il secondo no.

Lo sweep dei promemoria usa l'indice parziale: `Index Scan using lesson_reminder_due_idx`, 0,025 millisecondi.

## Alternative considerate

**Nessun indice in più.** Con i dati di oggi va bene. Ma una tabella di lezioni cresce sempre, e aggiungere un indice a una tabella grande in produzione è più delicato che farlo subito.

**Indici su ogni colonna filtrabile.** Ogni indice costa spazio e rallenta le scritture, perché va aggiornato a ogni INSERT e UPDATE. Abbiamo indicizzato solo le query misurate e frequenti.

**Un indice funzionale su `(start_time AT TIME ZONE ...)::date`.** Avrebbe permesso di tenere il filtro `__date`. Ma lega l'indice al fuso orario e alla forma esatta dell'espressione. L'intervallo sulla colonna è più semplice e più robusto.

## Errori comuni e trade-off

- **Funzioni sulla colonna nel WHERE**, come `__date`, `__year`, `Lower()`: disattivano l'indice normale.
- **Ordine sbagliato delle colonne** in un indice composto. La prima colonna deve essere quella filtrata per uguaglianza.
- **Fidarsi di EXPLAIN senza ANALYZE.** Senza ANALYZE vedi solo la stima del planner, non quello che succede davvero.
- **Testare con tabelle quasi vuote.** Con poche righe il planner preferisce leggere tutto, e sembra che l'indice non serva. Bisogna misurare con volumi realistici e dopo `ANALYZE`.
- **Creare indici su tabelle grandi in produzione.** `CREATE INDEX` blocca le scritture sulla tabella. Su tabelle grandi si usa `AddIndexConcurrently` di `django.contrib.postgres`. Noi non l'abbiamo usato perché oggi le tabelle sono piccole: è un trade-off da ricordare.

## Come lo spiegheresti a un colloquio

Ho aggiunto indici composti e parziali solo sulle query frequenti, dopo averle misurate con `EXPLAIN ANALYZE` su 200.000 righe. Per esempio un indice `(teacher_id, start_time)` per l'agenda settimanale e un indice parziale per i promemoria non ancora inviati. Ho anche trovato che il filtro `__date` di Django applica una funzione alla colonna e impedisce di usare l'indice. Ho sostituito il filtro con un intervallo di datetime: da 1.000 a 20 blocchi letti per la stessa query. So che ogni indice rallenta le scritture, quindi ne ho aggiunti pochi e motivati.

## Domande di autoverifica

1. **Perché `start_time__date__gte` non usa bene l'indice su `start_time`?**
   Perché in SQL diventa una conversione di fuso e un cast sulla colonna. Una funzione sulla colonna impedisce all'indice B-tree normale di essere usato per il filtro.

2. **Cos'è un indice parziale e quando conviene?**
   Un indice che include solo le righe che rispettano una condizione. Conviene quando le query cercano sempre un sottoinsieme piccolo, come le lezioni non ancora ricordate.

3. **Perché l'ordine delle colonne in un indice composto conta?**
   L'indice è ordinato per la prima colonna e poi per la seconda. Serve alle query che filtrano sulla prima colonna, non a quelle che filtrano solo sulla seconda.

4. **Cosa guardi per primo in un EXPLAIN ANALYZE?**
   Il tipo di scansione (Index o Seq Scan), le righe scartate dal filtro, i blocchi letti, e la differenza tra righe stimate e reali.

5. **Qual è il costo di un indice?**
   Spazio su disco e scritture più lente, perché ogni INSERT e UPDATE deve aggiornare anche l'indice. In più, crearlo su una tabella grande blocca le scritture, se non si usa la creazione concorrente.
