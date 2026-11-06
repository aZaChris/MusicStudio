# KB: La notte del cambio d'ora una lezione di 60 minuti durava due ore

## Sintomo
Test `test_overlap_uses_real_time_across_daylight_saving_change`: una lezione prenotata il 25/10/2026 alle 00:30 UTC per 60 minuti veniva salvata con fine alle 02:30 UTC. La prenotazione successiva, alle 01:30 UTC, riceveva un 409 anche se doveva essere libera.

## Causa radice
DRF converte i datetime in ingresso nel fuso corrente (`Europe/Rome`). In Python, sommare un `timedelta` a un datetime con `zoneinfo` lavora sull'**ora da orologio**: 02:30 CEST + 60 minuti = 03:30 ora locale. Ma quella notte alle 03:00 CEST si torna alle 02:00 CET, quindi 03:30 CET sono due ore reali dopo.

## Come l'abbiamo confermata
Un test temporaneo ha stampato la risposta e la riga nel database: `start_time` 00:30 UTC, `end_time` 02:30 UTC, risposta API `02:30+02:00` → `03:30+01:00`.

## Risoluzione
`end_of(start, minutes)` in `backend/apps/lessons/services.py` converte in UTC prima di sommare. Anche `Lesson.duration_minutes` sottrae in UTC: la sottrazione di due datetime con lo stesso `tzinfo` è anche lei aritmetica da orologio.

## Lezione per il futuro
Le **durate** si calcolano sempre in UTC. L'ora locale serve solo per i concetti "da calendario", come "lunedì alle 00:00" (dove infatti `week_bounds` lavora apposta in ora locale). Un test sulla notte del cambio d'ora costa poco e trova questi bug.

## Riferimenti
- `docs/learning/concetti/exclusion-constraint.md`
- Documentazione Python, `zoneinfo` e aritmetica dei datetime aware
