# KB: Due prenotazioni simultanee vanno in deadlock invece di dare 409

## Sintomo
Il test con due thread che prenotano lo stesso orario falliva con `OperationalError: deadlock detected`, `CONTEXT: while checking exclusion constraint on tuple ... in relation "lessons_lesson"`, invece di dare un 201 e un 409.

## Causa radice
Con un exclusion constraint PostgreSQL inserisce prima la riga e poi controlla il vincolo. Ognuna delle due transazioni trova la riga non ancora confermata dell'altra e aspetta la sua fine: si aspettano a vicenda. PostgreSQL rileva il ciclo e interrompe una delle due con SQLSTATE 40P01. Con un vincolo `UNIQUE` di solito la seconda aspetta e poi fallisce in modo pulito; con gli exclusion constraint il deadlock è un esito possibile (documentato).

## Come l'abbiamo confermata
Traceback del test: `Process A waits for ShareLock on transaction X; blocked by process B` e viceversa, durante il controllo del vincolo `lesson_no_teacher_overlap`.

## Risoluzione
`_guarded_write` in `backend/apps/lessons/services.py` esegue la scrittura in un savepoint. Se riceve un `DeadlockDetected` riprova (massimo 2 volte). Al nuovo tentativo la riga del vincitore è visibile e il vincolo dà una violazione normale, tradotta in 409. Il test ora passa 5 volte su 5; tre test unitari coprono retry, esaurimento dei retry ed errori di integrità diversi.

## Lezione per il futuro
Un vincolo che protegge da scritture concorrenti va provato **con scritture concorrenti vere** (thread e connessioni separate). Il codice che traduce gli errori del database deve prevedere anche il deadlock, non solo la violazione.

## Riferimenti
- `docs/learning/concetti/exclusion-constraint.md`
- Documentazione PostgreSQL, "Exclusion Constraints" e "Deadlocks"
