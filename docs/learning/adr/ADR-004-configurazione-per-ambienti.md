# ADR-004: Configurazione per ambienti con django-environ

- Stato: accettato
- Data: 2026-11-06

## Contesto

Esistevano `base.py`, `dev.py` e `prod.py`, ma: mancava un profilo di test; la produzione non sapeva di stare dietro un proxy TLS; gli entrypoint di produzione puntavano a un modulo vuoto; alcuni valori (path dell'admin, limiti, logging) erano fissi nel codice.

## Decisione

- Quattro moduli: `base` (comune, tutto da variabili d'ambiente), `dev`, `test`, `prod`.
- In `prod` i segreti si leggono **senza default** (`env("JWT_SIGNING_KEY")`). Se manca un valore, Django non parte e il messaggio nomina la variabile. Un test lo verifica.
- In `prod`: `SECURE_PROXY_SSL_HEADER`, perché Coolify termina il TLS e inoltra `X-Forwarded-Proto`. Poi redirect HTTPS (con eccezione per `/health/`), HSTS e cookie sicuri.
- `test` è deterministico: hasher veloce, cache in memoria, email in memoria, chiave fittizia.
- Ogni variabile è documentata in `.env.example`.

## Alternative scartate

- **Un solo file con molti `if`**: difficile da leggere, facile da sbagliare.
- **pydantic-settings**: validazione tipizzata, ma una dipendenza in più per un problema che django-environ già risolve.
- **Segreti con default "di comodo" anche in prod**: rischio di andare in produzione con una chiave nota.

## Conseguenze

- Una produzione configurata male si ferma all'avvio, non alla prima richiesta.
- Il build Docker deve passare valori fittizi a `collectstatic`, perché carica le impostazioni di produzione. È un compromesso visibile nel Dockerfile.
