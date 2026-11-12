# I dati dei fusi orari arrivavano per caso, da kombu

## Sintomo

Dopo l'aggiornamento di Celery 5.6 → 5.7 (PR #16 di Dependabot), `uv sync` ha disinstallato
`tzdata` senza installare niente al suo posto. Nessun test è fallito, la CI era verde e
l'applicazione in locale funzionava.

## Causa radice

- Django usa il modulo `zoneinfo` di Python per il fuso orario del progetto, `Europe/Rome`
  (`TIME_ZONE` in `config/settings/base.py`).
- `zoneinfo` cerca i dati prima nel sistema operativo (`/usr/share/zoneinfo`), poi nel
  pacchetto Python `tzdata`.
- Noi non avevamo mai dichiarato `tzdata`. Arrivava come dipendenza di **kombu**, la libreria
  di code di Celery. Kombu 5.7 ora lo chiede solo su Windows
  (`marker = "sys_platform == 'win32'"` nel lock).
- In locale (WSL) e sul runner Ubuntu della CI i dati di sistema ci sono, quindi niente si
  accorgeva della differenza.
- L'immagine di produzione parte da `python:3.12-slim-bookworm`. Debian bookworm installa il
  pacchetto di sistema `tzdata` di base, quindi oggi funziona. In Debian trixie non è più tra i
  pacchetti di base: con un aggiornamento dell'immagine Django non sarebbe partito.

## Come l'abbiamo confermata

- Il diff di `uv sync` mostrava `- tzdata==2026.4` senza un `+`.
- Nel lock prima del cambio, kombu aveva `{ name = "tzdata" }` senza marker; dopo il cambio,
  con il marker `win32`.
- Un test che svuota il percorso di ricerca di `zoneinfo` (`reset_tzpath(to=[])`) e carica
  `Europe/Rome` falliva con `ZoneInfoNotFoundError`: è la situazione di un'immagine senza dati
  di sistema.

## Risoluzione

- `tzdata` è dichiarato in `backend/pyproject.toml`, con un commento che spiega il motivo.
- `config/tests/test_timezone_data.py` carica il fuso orario del progetto usando solo il
  pacchetto `tzdata`. Se la dipendenza sparisce di nuovo, la CI diventa rossa anche su un
  runner che ha i dati di sistema.

## Lezione per il futuro

- Se il codice usa direttamente una libreria, dichiarala, anche se oggi arriva già tramite
  un'altra. Le dipendenze transitive possono cambiare a ogni aggiornamento minor.
- Leggi il diff di `uv sync` o di `npm ci` dopo un aggiornamento: una riga con solo `-` è un
  pacchetto che il progetto non chiede più a nessuno.
- Un test verde su un ambiente "ricco" (CI, laptop) non prova che l'immagine di produzione
  abbia le stesse cose. Il test deve togliere esplicitamente l'aiuto dell'ambiente.

## Riferimenti

- `backend/pyproject.toml`, `backend/config/tests/test_timezone_data.py`
- Documentazione di Python, modulo `zoneinfo`, sezione "Data sources":
  https://docs.python.org/3/library/zoneinfo.html#data-sources
- PR #16 (Celery 5.7, kombu 5.7)
