# KB: Il virtualenv sparisce nel container di sviluppo

## Sintomo
Con il vecchio `infra/docker-compose.yml` il backend non poteva trovare Django né gunicorn, pur avendo installato le dipendenze nell'immagine.

## Causa radice
Il Dockerfile creava il virtualenv in `/app/.venv` (default di `uv sync` nella directory del progetto). Il Compose di sviluppo montava `../backend:/app`: il bind mount copre l'intero contenuto di `/app` dell'immagine, `.venv` compreso. Sull'host `backend/.venv` è ignorato o diverso (altra piattaforma).

## Come l'abbiamo confermata
Lettura di Dockerfile e Compose: `WORKDIR /app`, `uv sync` senza `UV_PROJECT_ENVIRONMENT`, `ENV PATH=/app/.venv/bin`, volume `../backend:/app`. Il task T055 della feature 001 ("eseguire il Compose end-to-end") era rimasto aperto: lo stack non era mai stato avviato.

## Risoluzione
`UV_PROJECT_ENVIRONMENT=/opt/venv` nel builder e `PATH=/opt/venv/bin` nel runtime (`backend/Dockerfile`). Il mount del sorgente su `/app` non tocca più le dipendenze.

## Lezione per il futuro
Quando monti il sorgente in un container, tieni le dipendenze installate **fuori** dalla cartella montata. E un Compose "scritto ma mai avviato" va considerato non funzionante finché non lo provi.

## Riferimenti
- `docs/learning/concetti/docker-e-deploy-con-coolify.md`
- Documentazione uv: variabile `UV_PROJECT_ENVIRONMENT`
