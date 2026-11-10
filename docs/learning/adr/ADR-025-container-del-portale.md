# ADR-025: Il container del portale web su Coolify

- Stato: accettato
- Data: 2026-11-10

## Contesto

Il proprietario porta il portale su Coolify dopo la review di un amico, con due richieste: codice pulito e sicuro, e nessuna porta esposta. L'immagine di produzione esistente usava `nginx:alpine` senza versione fissata, girava come root, non aveva il fallback delle rotte (ricaricare `/students` dava 404) e non mandava intestazioni di sicurezza. Nel compose di Coolify il portale non c'era.

## Decisione

- **Immagine**: build su `node:22.12.0-alpine`, esecuzione su `nginxinc/nginx-unprivileged:1.27.3-alpine`. Versioni fissate; nginx gira come utente 101, sulla porta 8080.
- **Nessuna porta pubblicata**: il servizio `web` del compose ha solo `expose`. Il dominio si imposta in Coolify, e il suo proxy instrada. Un test del backend fallisce se un servizio pubblica una porta o perde l'healthcheck.
- **Configurazione di nginx** come template, completato all'avvio con `API_ORIGIN`:
  - fallback: ogni percorso che non è un file riceve `index.html`;
  - cache: un anno per i file con l'hash nel nome, nessuna cache per `index.html`;
  - `/healthz` per l'healthcheck;
  - `server_tokens off`, che nasconde la versione di nginx.
- **Intestazioni di sicurezza**, dichiarate una volta a livello di server. Un `add_header` dentro una `location` le sostituirebbe tutte, quindi le `location` non ne usano:
  - `Content-Security-Policy`: script, stili e font solo dal portale stesso, connessioni solo verso il portale e l'origine delle API, nessun iframe da altri siti, niente plugin;
  - `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (browser vecchi), `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` che spegne fotocamera, microfono, posizione e pagamenti, `Cross-Origin-Opener-Policy: same-origin`;
  - HSTS lo imposta il proxy di Coolify, che termina l'HTTPS.
- **Fallire subito**: uno script all'avvio del container controlla `API_ORIGIN`. Se manca o non è `https://` (o localhost), il container non parte.
- **Origini separate**: portale e API hanno domini diversi. Le API accettano chiamate dal browser solo dall'origine del portale (`CORS_ALLOWED_ORIGINS`).
- **Prova in CI**: il job `web-image` costruisce l'immagine, la avvia e controlla utente, fallback, health, intestazioni e il rifiuto di partire senza `API_ORIGIN`.

## Alternative scartate

- **Portale e API sullo stesso dominio**, con nginx che inoltra `/api` al backend. Niente CORS, ma le richieste del portale passerebbero da due proxy e quelle del mobile da uno. `TRUSTED_PROXY_COUNT` (ADR-021) sarebbe giusto per un percorso e sbagliato per l'altro, e il limite sui tentativi di login tornerebbe aggirabile.
- **Servire il portale da Django** con whitenoise: deploy legati e CSP diverse per percorso.
- **Un server statico in Node**: immagine più grande e più superficie d'attacco.

## Conseguenze

- Cambiare l'indirizzo delle API richiede di ricostruire il portale, perché entra nel bundle.
- La CSP vieta gli script inline: chi aggiunge uno snippet di analytics dovrà servirlo come file.
- In locale, senza Docker, nginx non è stato provato: lo prova la CI.
