# KB: I budget di query nei test erano più bassi della realtà

## Sintomo
I test con `django_assert_num_queries` misuravano una query in meno del previsto. Dopo una prima correzione, la prima misura era giusta e la seconda, sullo stesso client, di nuovo una in meno.

## Causa radice
`APIClient.force_authenticate(user=...)` riusa l'oggetto utente passato. L'utente creato da `TeacherFactory` ha già in cache il profilo `user.teacher`, quindi la query che una richiesta reale fa per caricarlo non veniva contata. Riusando lo stesso client per due misure, la cache si formava alla prima richiesta.

## Come l'abbiamo confermata
Confronto dei conteggi con utente della factory, con utente ricaricato dal database e con client nuovo per ogni misura: le differenze erano sempre esattamente di una query, quella del profilo.

## Risoluzione
`client_for` in `backend/apps/common/tests/helpers.py` autentica una copia fresca dell'utente (`User.objects.get(pk=...)`), e `test_num_queries.py` crea un client nuovo per ogni misura.

## Lezione per il futuro
Un test di performance deve riprodurre lo stato di una richiesta reale, cache comprese. Con JWT reale va aggiunta anche la query che carica l'utente dal token.

## Riferimenti
- `docs/learning/concetti/orm-e-problema-n-piu-1.md`
