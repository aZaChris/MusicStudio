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
| [riga-di-errore-django-senza-request-id.md](riga-di-errore-django-senza-request-id.md) | La riga `django.request` arrivava dopo il middleware, che aveva già azzerato il request id |
| [rtk-nasconde-errori-di-pytest.md](rtk-nasconde-errori-di-pytest.md) | Il filtro di rtk mostrava "22 passed" nascondendo un errore: `rtk proxy` per i controlli |
| [seed-con-hasher-diverso-login-401.md](seed-con-hasher-diverso-login-401.md) | Seed del load test con i settings di test (MD5): ogni login in produzione dava 401 |
| [contratto-openapi-campi-nullabili.md](contratto-openapi-campi-nullabili.md) | Generando i tipi per i client: un'azione con il tipo sbagliato e tre campi null non dichiarati |
| [senza-redis-ogni-richiesta-aspetta-il-timeout.md](senza-redis-ogni-richiesta-aspetta-il-timeout.md) | Senza Redis i throttle falliscono aperti ma dopo il timeout: ogni richiesta lenta |
| [portale-disconnesso-dopo-30-minuti.md](portale-disconnesso-dopo-30-minuti.md) | Il portale non salvava il refresh token ruotato: utenti disconnessi dopo ~30 minuti |
| [vitest-worker-non-partono-poca-ram.md](vitest-worker-non-partono-poca-ram.md) | Worker di Vitest che non partono e timeout con poca RAM: 2 worker e attese più lunghe |
| [coolify-build-arg-vuoti-collectstatic.md](coolify-build-arg-vuoti-collectstatic.md) | Coolify passa ogni variabile, anche vuota, alla build e a tutti i container: `collectstatic`, worker e beat crashavano su un int vuoto |
| [celery-scrive-i-token-nei-log.md](celery-scrive-i-token-nei-log.md) | Il log di fine task di Celery includeva gli argomenti, quindi il token d'invito in chiaro: un filtro li toglie |
| [ci-rossa-dopo-mezzanotte-seed-demo.md](ci-rossa-dopo-mezzanotte-seed-demo.md) | Una data UTC confrontata con `__date` in ora di Roma: la CI falliva solo tra le 23 e le 01 |
| [audit-operatore-invisibile-al-titolare.md](audit-operatore-invisibile-al-titolare.md) | Sblocco e reset MFA dell'operatore salvati senza studio né autore: esistevano nel log ma il titolare non li vedeva |
| [font-titoli-tema-chiaro.md](font-titoli-tema-chiaro.md) | Nel tema chiaro i titoli usavano il font di ripiego: l'override di `--font-display` perdeva per specificità contro il selettore dei token |
| [tzdata-sparito-con-kombu.md](tzdata-sparito-con-kombu.md) | Celery 5.7 ha tolto `tzdata` su Linux: i fusi orari arrivavano per caso da kombu; ora è dichiarato e un test lo garantisce |
| [packaging-mancante-nell-immagine-celery.md](packaging-mancante-nell-immagine-celery.md) | `worker` e `beat` in crash-loop su Coolify: kombu 5.7 importa `packaging` senza dichiararlo e l’immagine usa `--no-dev`; ora è dichiarato e la build lo verifica |
| [gunicorn-control-socket-permesso-negato.md](gunicorn-control-socket-permesso-negato.md) | Gunicorn 25.1+ apre un socket di controllo in `$HOME`; il container non root non ha una home scrivibile e loggava `Permission denied`: ora è disattivato |
