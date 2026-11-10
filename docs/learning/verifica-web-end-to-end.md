# Verifica end-to-end del portale web contro il backend Django

Questo documento registra la prova del portale web contro il backend vero. I test con Vitest provano il codice della SPA con la rete simulata; qui la build di produzione della SPA parla con Django, che parla con PostgreSQL.

## Come è stata fatta

- **Data**: 10 novembre 2026.
- **Backend**: branch `refactor/production-standards`, server di sviluppo di Django sulla porta 8000, PostgreSQL 16 locale, dati da `manage.py seed_demo`, `CORS_ALLOWED_ORIGINS=http://localhost:4173`. Redis non è installato su questa macchina: un file di settings tenuto fuori dal repository usa una cache in memoria, altrimenti ogni controllo dei throttle aspetta il timeout di connessione a Redis.
- **Portale**: build di produzione con `VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1`, servita con `vite preview` sulla porta 4173.
- **Guida**: lo script `frontend/scripts/verify-django.mjs` (Playwright con Chromium). Alcuni passi chiedono conferma direttamente alle API.

## Risultato

```
PASS  opens on the login page without a session
PASS  wrong password shows 'Invalid email or password.'
PASS  owner signs in and sees the server's dashboard counts
PASS  completing a lesson with a note is saved on the server
PASS  reloading a deep route keeps the portal (route fallback) and shows the student
PASS  a cash payment is registered with today's local date
PASS  the access token is not in localStorage; the refresh token is
PASS  logout returns to login and the old refresh token is refused by the server
PASS  parent sees the read-only portal
PASS  no uncaught errors in the page

10/10 steps passed
```

Il quinto passo prova anche il rinnovo della sessione al caricamento della pagina. Ricaricando un indirizzo interno, il token di accesso in memoria sparisce; il portale usa il refresh token salvato, ottiene un nuovo token e mostra la pagina senza chiedere il login.

L'ottavo passo è quello di sicurezza: il refresh token letto prima del logout, rimandato al server dopo il logout, riceve 401.

## Cosa è andato storto durante la prova

- **Dati consumati.** Un secondo lancio sullo stesso database falliva: il primo aveva già completato l'unica lezione programmata del seed. Ogni prova va fatta su un database appena creato.
- **Una richiesta lenta.** In un lancio il completamento della lezione ha impiegato 9 secondi e lo script, che aspettava 10 secondi la chiusura della finestra, è fallito. Nel log di Django non c'erano errori; nel lancio successivo la stessa richiesta ha impiegato 1 secondo. La macchina era carica. L'attesa è stata portata a 30 secondi.
- **Un difetto di layout trovato guardando gli screenshot.** Il riquadro con "Log out" in fondo alla barra laterale usciva dallo schermo: la barra aveva altezza minima pari alla finestra più il padding. Corretto con `box-sizing: border-box`.

## Cosa non è stato verificato qui

- **nginx.** Qui il fallback delle rotte lo fa `vite preview`. Il server di produzione è nginx, che su questa macchina non c'è, e nemmeno Docker. L'immagine vera, con utente non root, fallback, intestazioni di sicurezza, health check e rifiuto di partire senza `API_ORIGIN`, la costruisce e la prova il job `web-image` della CI su GitHub Actions a ogni push.
- **Il deploy su Coolify**, con HTTPS e i domini veri.
