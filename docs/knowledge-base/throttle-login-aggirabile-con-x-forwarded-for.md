# KB: Il limite sui tentativi di login si aggirava con X-Forwarded-For

## Sintomo
Nessun sintomo visibile: è emerso rileggendo il codice durante il giro OWASP della fase 4. Il test esistente `test_login_is_throttled_after_five_attempts` passava, perché manda tutte le richieste senza l'header `X-Forwarded-For`. Ma un client che manda un valore diverso di `X-Forwarded-For` a ogni tentativo poteva provare password senza limite.

## Causa radice
I throttle di DRF identificano il client con `SimpleRateThrottle.get_ident()`. Se l'impostazione `NUM_PROXIES` non è definita (il default di DRF è `None`), la funzione usa come identità **l'intero** header `X-Forwarded-For`, tolti gli spazi. Quell'header lo scrive il client. Quindi ogni valore inventato crea un contatore nuovo, che parte da zero. Il problema c'era anche senza proxy: l'header lo può mandare chiunque, direttamente.

## Come l'abbiamo confermata
Lettura del sorgente di DRF (`rest_framework/throttling.py`, `get_ident`): con `num_proxies is None` restituisce `''.join(xff.split())`. Poi il test `test_forged_forwarded_for_cannot_reset_the_login_throttle`: sei tentativi sbagliati, ognuno con un `X-Forwarded-For` diverso a sinistra. Con `NUM_PROXIES` a `None` il sesto tentativo riceve 401, cioè nessun limite; con il valore corretto riceve 429.

## Risoluzione
`REST_FRAMEWORK["NUM_PROXIES"] = TRUSTED_PROXY_COUNT` in `backend/config/settings/base.py`, e di nuovo in `prod.py`, dove `TRUSTED_PROXY_COUNT` vale 1 (Traefik di Coolify). Con 0 DRF usa l'indirizzo della connessione; con 1 usa l'ultimo valore dell'header, quello aggiunto dal nostro proxy. È la stessa regola di `client_ip()` (ADR-021): una sola impostazione decide quanti proxy sono fidati, per tutti.

## Lezione per il futuro
Ogni volta che un componente "trova l'IP del client", va controllato **come** lo trova. I default delle librerie sono pensati per funzionare ovunque, non per essere sicuri dietro il tuo proxy. E un test di sicurezza deve provare anche l'attacco, non solo il caso normale: il vecchio test non mandava mai l'header.

## Riferimenti
- `docs/learning/adr/ADR-021-allowlist-webhook-e-ip-reale.md`
- `docs/learning/concetti/sicurezza-api-owasp.md` (API2 e API4)
- `backend/apps/accounts/tests/test_auth.py`
