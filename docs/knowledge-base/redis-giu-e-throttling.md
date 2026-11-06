# KB: Con Redis spento tutta l'API rispondeva 500

## Sintomo
Test `test_cache_outage_falls_back_to_computing`: con la cache simulata come irraggiungibile, `GET /api/v1/dashboard/` rispondeva **500** anche se la cache della dashboard ricadeva correttamente sul calcolo. Lo stesso valeva per qualsiasi endpoint.

## Causa radice
I throttle di DRF (`AnonRateThrottle`, `UserRateThrottle`, `ScopedRateThrottle`) leggono e scrivono i contatori nella cache di Django, cioè Redis. Il backend `RedisCache` non assorbe gli errori di connessione, quindi `allow_request` solleva un'eccezione a ogni richiesta, prima ancora della vista. Un guasto della cache diventava un guasto di tutta l'API.

## Come l'abbiamo confermata
Il traceback del 500 partiva da `SimpleRateThrottle.allow_request` → `cache.get`, non dal codice della dashboard. Un secondo test su `/api/v1/students/`, che non usa la cache della dashboard, dava lo stesso 500.

## Risoluzione
`backend/apps/common/throttling.py`: sottoclassi dei tre throttle con un `allow_request` che, se la cache solleva un'eccezione, scrive l'errore nel log e lascia passare la richiesta ("fail open"). Configurate in `REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"]` e nella vista di login. Test di regressione `test_redis_outage_does_not_take_the_api_down`.

## Lezione per il futuro
Ogni dipendenza "accessoria" (cache, metriche, rate limiting) va provata **spenta**: deve degradare il servizio, non abbatterlo. La scelta fail open o fail closed va fatta in modo esplicito: qui fail open, quindi durante un guasto di Redis non c'è rate limiting, nemmeno sul login.

## Riferimenti
- `docs/learning/concetti/caching.md`
- `docs/learning/adr/ADR-017-cache-dashboard-con-versioni.md`
