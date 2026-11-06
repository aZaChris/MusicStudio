# ADR-012: Il contratto OpenAPI è versionato nel repository

- Stato: accettato
- Data: 2026-11-06

## Contesto

Due client usano questa API: la SPA web e, in futuro, l'app mobile. Lo schema OpenAPI veniva generato solo a runtime. Un cambio in un serializer poteva rompere i client senza che nessuno lo notasse in revisione. E gli errori che un client deve gestire non erano documentati.

## Decisione

- Lo schema è generato da drf-spectacular e salvato in `backend/openapi.yaml`.
- Un test, uno step di CI e un hook pre-commit lo rigenerano e falliscono se differisce dal file salvato. Ogni cambio di contratto appare nel diff della pull request.
- Ogni operazione ha un **tag** con il dominio (lessons, payments, eccetera), calcolato dal modulo della vista (`MusicStudioAutoSchema.get_tags`).
- Un **postprocessing hook** (`backend/apps/common/schema.py`) aggiunge gli schemi comuni `Error` e `ValidationError` e le risposte 400/401/403/404/409/429 dove servono.
- `COMPONENT_SPLIT_REQUEST`: schemi separati per richiesta e risposta, così i campi in sola lettura non sembrano obbligatori in input.

## Alternative scartate

- **`@extend_schema(responses=...)` su ogni vista**: ripetitivo e facile da dimenticare su una vista nuova.
- **Schema solo a runtime**: nessuna revisione dei cambi di contratto.
- **Contract-first** (scrivere l'OpenAPI a mano e poi il codice): ottimo per API con molti team. Qui il codice è la fonte, e lo schema si controlla.

## Conseguenze

- Ogni modifica a serializer o viste richiede di rigenerare il file. Il messaggio del test dice il comando esatto.
- Il file è grande e generato: va escluso dagli hook che riformattano, altrimenti il confronto fallisce.
- Le regole del hook sono euristiche (per esempio, 409 solo sulle scritture delle lezioni). Se aggiungiamo un nuovo tipo di conflitto, va aggiornato il hook.
