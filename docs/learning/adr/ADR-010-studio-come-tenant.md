# ADR-010: Lo studio è il tenant

- Stato: accettato
- Data: 2026-11-06

## Contesto

Nella fase 1 un insegnante solista non aveva uno studio, e la visibilità era decisa da tre rami di codice, uno per ruolo. In quel codice la fase 1 aveva trovato due fughe di dati. Con più ruoli e più funzioni, il rischio cresce.

## Decisione

- Lo **studio** è il tenant. Ogni insegnante appartiene a esattamente uno studio (`NOT NULL`, `on_delete=PROTECT`). Un solista ha uno studio personale che possiede.
- Ogni **allievo** ha il suo studio, sempre uguale a quello del suo insegnante. Lezioni, pacchetti e pagamenti raggiungono lo studio attraverso l'allievo.
- A ogni richiesta un `TenantContext` (ruolo, studio, profilo insegnante o genitore) viene calcolato con **una query** e messo in cache sulla richiesta Django (`backend/apps/common/tenancy.py`).
- Lo scoping (`backend/apps/common/scoping.py`) riceve il contesto e, per ogni modello, i "percorsi" verso studio, insegnante e genitore (`TenantPaths`).
- Le migrazioni creano gli studi personali e riempiono lo studio degli allievi. Un test applica le migrazioni vere a dati nel formato della fase 1.

## Alternative scartate

- **`studio_id` su ogni tabella**: filtri più diretti, ma quattro posti in cui mantenere la coerenza. Lo valuteremo se il profiling lo chiederà.
- **Uno schema PostgreSQL per tenant** (django-tenants): migrazioni moltiplicate per il numero di studi. Eccessivo per studi da 1 a 10 insegnanti.
- **Un database per tenant**: ancora più costoso da gestire.
- **Row Level Security di PostgreSQL**: la garanzia più forte, ma richiede di passare il tenant alla connessione a ogni richiesta. Da rivalutare nella fase 4.
- **Middleware per il contesto**: non funziona, perché l'autenticazione JWT avviene dentro DRF, dopo i middleware.
- **Thread-local o contextvars**: stato globale implicito, rischioso se non viene azzerato.

## Conseguenze

- Il confine del tenant è una colonna, non una convenzione.
- La coerenza `allievo.studio == insegnante.studio` è garantita dai service, non dal database. È un punto debole dichiarato.
- Un genitore non appartiene a uno studio: vede i figli tramite i collegamenti, anche se sono in studi diversi.
- I budget di query sono rimasti uguali.
