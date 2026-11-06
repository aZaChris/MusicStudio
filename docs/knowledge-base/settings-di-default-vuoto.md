# KB: Gli entrypoint di produzione puntavano a un modulo di settings vuoto

## Sintomo
Nessun sintomo visibile finché `DJANGO_SETTINGS_MODULE` è impostata dall'esterno. Senza, gunicorn avrebbe caricato impostazioni vuote e Celery quelle di sviluppo.

## Causa radice
`config/wsgi.py` e `config/asgi.py` avevano `setdefault("DJANGO_SETTINGS_MODULE", "config.settings")`, residuo del template di `startproject`. Ma `config/settings/` era stato trasformato in un package con `__init__.py` vuoto. `config/celery.py` usava `config.settings.dev`. Funzionava solo perché `infra/.env` impostava la variabile.

## Come l'abbiamo confermata
`grep settings config/*.py manage.py` e lettura di `config/settings/__init__.py` (vuoto).

## Risoluzione
I tre entrypoint di produzione (wsgi, asgi, celery) usano `config.settings.prod`. `manage.py` resta su `dev`. L'immagine Docker imposta comunque la variabile in modo esplicito.

## Lezione per il futuro
Quando dividi `settings.py` in un package, aggiorna **tutti** i default: `manage.py`, `wsgi.py`, `asgi.py`, `celery.py`, pytest e mypy. Un default deve fallire in modo sicuro, non dipendere da un `.env` presente per caso.

## Riferimenti
- `docs/learning/concetti/configurazione-per-ambienti.md`
