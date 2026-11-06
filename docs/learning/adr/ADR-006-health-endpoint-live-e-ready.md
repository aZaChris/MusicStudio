# ADR-006: Due health endpoint, liveness e readiness

- Stato: accettato
- Data: 2026-11-06

## Contesto

Docker e Coolify devono sapere se un container funziona. Prima non esisteva nessun endpoint dedicato.

## Decisione

- `GET /health/live/`: risponde 200 se il processo Python risponde. Non tocca database né Redis.
- `GET /health/ready/`: esegue `SELECT 1` su PostgreSQL e `PING` su Redis. Risponde 200 se entrambi rispondono, 503 se uno fallisce, con il dettaglio di quale.
- Sono view Django semplici: niente autenticazione, niente throttling, esenti dal redirect HTTPS (i probe arrivano in HTTP dalla rete interna).
- Il `HEALTHCHECK` del Dockerfile usa la liveness. Nel Compose di Coolify il servizio `backend` usa la readiness, perché Coolify usa lo stato di salute per decidere se un deploy è riuscito.
- Il probe è uno script Python della libreria standard (`backend/docker/healthcheck.py`), perché l'immagine slim non ha curl.

## Alternative scartate

- **Un solo endpoint che controlla tutto**: durante un guasto del database, un orchestratore che riavvia i container "non sani" riavvierebbe anche web perfettamente funzionanti, peggiorando il guasto.
- **django-health-check**: completo, ma per due controlli è una dipendenza in più.

## Conseguenze

- Gli endpoint sono pubblici. Non rivelano versioni né dettagli degli errori, solo `ok` o `error` per controllo.
- Docker da solo non riavvia un container "unhealthy": lo segnala. Il riavvio automatico dipende dall'orchestratore.
