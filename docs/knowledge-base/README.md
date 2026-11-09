# Knowledge base

Problemi non banali risolti nel progetto: sintomo, causa radice, verifica, soluzione e lezione.

| File | In breve |
| --- | --- |
| [scritture-cross-tenant-nei-serializer.md](scritture-cross-tenant-nei-serializer.md) | I campi di relazione DRF accettavano id di altri tenant (BOLA in scrittura) |
| [venv-nascosto-dal-bind-mount.md](venv-nascosto-dal-bind-mount.md) | Il mount del sorgente su `/app` nascondeva il virtualenv dell'immagine |
| [settings-di-default-vuoto.md](settings-di-default-vuoto.md) | wsgi/asgi/celery puntavano a un package di settings vuoto o di sviluppo |
| [budget-query-falsati-da-force-authenticate.md](budget-query-falsati-da-force-authenticate.md) | `force_authenticate` riusava un utente con il profilo in cache |
| [pre-commit-e-core-hookspath.md](pre-commit-e-core-hookspath.md) | `pre-commit install` rifiuta con un `core.hooksPath` globale: hook versionati |
| [fine-lezione-e-ora-legale.md](fine-lezione-e-ora-legale.md) | Sommare minuti in ora di Roma sbagliava la durata la notte del cambio d'ora |
| [deadlock-su-exclusion-constraint.md](deadlock-su-exclusion-constraint.md) | Inserimenti simultanei sullo stesso orario: deadlock gestito con retry, poi 409 |
| [redis-giu-e-throttling.md](redis-giu-e-throttling.md) | I throttle DRF leggono da Redis: con Redis giù ogni richiesta dava 500; ora falliscono aperti |
| [throttle-login-aggirabile-con-x-forwarded-for.md](throttle-login-aggirabile-con-x-forwarded-for.md) | Senza `NUM_PROXIES` il throttle del login usava tutto `X-Forwarded-For`: tentativi illimitati |
