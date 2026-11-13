# KB: La CI diventava rossa solo dopo le 23 UTC

## Sintomo
Il job del backend è fallito, su PostgreSQL 16 e 18, con `lesson_no_teacher_overlap` dentro `test_seed_demo`. Il commit che l'ha fatto scattare non toccava il backend. Lo stesso test passava un'ora prima.

## Causa radice
`seed_demo` crea una lezione "tra 24 ore" e controlla di non averla già creata con `start_time__date=<data>`. Il filtro `__date` confronta nel **fuso corrente** (Europe/Rome), ma la data passata era presa dall'istante in **UTC**. Tra le 22:00 e le 24:00 UTC le due date sono diverse (a Roma è già il giorno dopo): la seconda esecuzione non trovava la lezione, ne inseriva una identica e il vincolo di esclusione sulle lezioni dell'insegnante la rifiutava. Il vincolo ha fatto il suo lavoro: ha trasformato un errore di fuso in un errore visibile.

## Come l'abbiamo confermata
Il fallimento riportava due intervalli identici alle 23:00 UTC. In locale, ora UTC 23:01, anche il test originale falliva. Un test nuovo che fissa l'ora a 10, 22 e 23 UTC lo riproduce e passa solo con la correzione.

## Risoluzione
`timezone.localtime(reminder_time).date()` al posto di `reminder_time.date()` in `seed_demo`. Il test `test_seed_demo_stays_idempotent_whatever_the_hour` copre le tre ore.

## Lezione per il futuro
È lo stesso errore già visto con le durate: un confronto tra date va fatto nello stesso fuso da entrambe le parti. Un test che dipende dall'ora del giorno non fallisce quando lo si scrive, ma quando la CI gira a un'ora sfortunata. I test che usano "adesso" vanno provati con l'ora fissata a più valori, soprattutto vicino a mezzanotte e al cambio dell'ora.

## Riferimenti
- `backend/apps/common/management/commands/seed_demo.py`, `backend/apps/common/tests/test_seed_demo.py` (rimossi il 13 novembre 2026 insieme ai dati demo: la lezione sul confronto tra giorno UTC e giorno di Roma resta valida)
- `docs/knowledge-base/fine-lezione-e-ora-legale.md` (lo stesso tipo di errore sulle durate)
