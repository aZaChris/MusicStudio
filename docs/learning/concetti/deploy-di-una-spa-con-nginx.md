# Deploy di una SPA con nginx, senza porte esposte

## TL;DR

Una SPA in produzione è un insieme di file statici, ma servirli bene non è banale. Bisogna gestire le rotte del client, la cache, le intestazioni di sicurezza e l'utente con cui gira il server. In MusicStudio il portale gira su nginx senza privilegi, in un'immagine con versioni fissate. Non pubblica porte: lo raggiunge solo il proxy di Coolify. E una CI costruisce e prova l'immagine vera a ogni push.

## Il problema reale

Il proprietario porta il portale su Coolify, e prima un amico rivede il codice. La richiesta era chiara: codice pulito, sicuro, nessuna porta esposta.

L'immagine che c'era aveva quattro problemi:

1. `FROM nginx:alpine`: un'etichetta mobile, quindi due build a distanza di un mese potevano usare versioni diverse;
2. nginx girava come root dentro il container;
3. nessun fallback per le rotte: ricaricare `/students` dava 404, perché sul disco non esiste un file `students`;
4. nessuna intestazione di sicurezza.

E nel compose di Coolify il portale non c'era proprio.

## Come funziona

Pensa a una biblioteca con un solo libro, `index.html`, che contiene tutte le pagine. Chi chiede "il capitolo studenti" deve ricevere quel libro, non sentirsi dire "non esiste". Questo è il **fallback**: ogni percorso che non è un file reale riceve `index.html`, e poi è il router della SPA a mostrare la pagina giusta.

Altri concetti:

- **Cache**: Vite mette un hash nel nome dei file (`index-BT7HOSvC.js`). Un file così non cambia mai: si può tenere in cache per un anno. `index.html` invece cambia a ogni deploy e non va tenuto in cache, altrimenti il browser continua a usare la versione vecchia.
- **Utente non root**: se un attaccante sfrutta una falla del server, si ritrova con i permessi dell'utente del processo. Meglio che non sia l'amministratore.
- **Nessuna porta pubblicata**: su Coolify il proxy Traefik riceve l'HTTPS sul dominio e inoltra al container nella rete interna. Una porta pubblicata sull'host scavalcherebbe il proxy e il suo HTTPS.

## Come lo abbiamo applicato in MusicStudio

**Il Dockerfile**, in `frontend/Dockerfile`, ha tre stadi: uno per lo sviluppo, uno di build e uno di produzione.

```dockerfile
FROM base AS build
ARG VITE_API_BASE_URL
RUN test -n "$VITE_API_BASE_URL" || { echo "VITE_API_BASE_URL build arg is required" >&2; exit 1; }
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27.3-alpine AS prod
COPY --chmod=755 nginx/05-require-api-origin.sh /docker-entrypoint.d/05-require-api-origin.sh
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
```

L'indirizzo delle API entra nel bundle al momento della build: senza, la build si ferma. L'immagine finale è `nginx-unprivileged`, che gira come utente 101 sulla porta 8080.

**La configurazione di nginx** è un template: all'avvio l'immagine sostituisce `${API_ORIGIN}` con il valore dell'ambiente. Le regole principali:

```nginx
location /assets/ { expires 1y;  try_files $uri =404; }
location /        { expires -1;  try_files $uri $uri/ /index.html; }
location = /healthz { return 200 "ok\n"; }
```

**Una trappola di nginx.** Le intestazioni di sicurezza sono dichiarate una sola volta, a livello di server. Se una `location` usasse a sua volta `add_header`, nginx **sostituirebbe** quelle del server invece di aggiungerle, e la CSP sparirebbe da quelle risposte. Per questo la cache si imposta con `expires` e non con `add_header Cache-Control`.

**Fallire subito.** Uno script in `/docker-entrypoint.d/` controlla `API_ORIGIN` all'avvio. Se manca o non inizia con `https://`, il container non parte. Meglio un deploy che fallisce in modo visibile di un portale che parte con una CSP rotta e non riesce a chiamare le API.

**Il compose di Coolify.** Il servizio `web` ha `expose: ["8080"]` e nessun `ports`. `API_PUBLIC_URL` è obbligatoria e serve due volte: nella build e nella CSP. Il CORS del backend, per default, accetta solo l'origine del portale.

**Un test che protegge la regola.** `backend/config/tests/test_deploy_compose.py` legge il compose e fallisce se un servizio pubblica una porta o non ha un healthcheck. La regola "nessuna porta esposta" non dipende più dalla memoria di chi modifica il file.

**La prova dell'immagine vera.** Su questa macchina Docker non c'è. Il job `web-image` della CI la costruisce e la avvia, poi controlla:
- che l'utente non sia root;
- che il container rifiuti di partire senza `API_ORIGIN`;
- che `/students/42` restituisca il portale;
- che `/healthz` risponda;
- che ci siano le intestazioni di sicurezza, e che nginx non dichiari la sua versione.

## Alternative considerate

**Portale e API sullo stesso dominio**, con nginx che inoltra `/api` al backend. Elimina il CORS, ma le richieste del portale passerebbero da due proxy e quelle del mobile da uno solo. L'impostazione sul numero di proxy fidati (`TRUSTED_PROXY_COUNT`) sarebbe giusta per un percorso e sbagliata per l'altro, e il limite sui tentativi di login tornerebbe aggirabile.

**Servire il portale da Django** con whitenoise: un solo servizio, ma deploy legati e intestazioni diverse per percorso.

**Un server statico in Node**: immagine più grande e più superficie d'attacco per servire file statici.

## Errori comuni e trade-off

- **Etichette mobili** come `nginx:alpine`: build diverse senza che nessuno lo sappia.
- **Dimenticare il fallback**: tutto funziona finché qualcuno non ricarica una pagina interna.
- **`add_header` dentro una `location`**: le intestazioni del server spariscono in silenzio.
- **Mettere in cache `index.html`**: gli utenti vedono la versione vecchia dopo un deploy.
- **Trade-off:** l'indirizzo delle API è nel bundle; per cambiarlo bisogna ricostruire il portale. In cambio, nessuna configurazione a runtime da proteggere.

## Come lo spiegheresti a un colloquio

Il portale è servito da nginx senza privilegi, in un'immagine con versioni fissate. Non pubblica porte: lo raggiunge solo il proxy di Coolify, e un test del backend fallisce se qualcuno aggiunge una porta al compose. nginx fa il fallback delle rotte, tiene in cache per un anno i file con l'hash e mai `index.html`, e manda una CSP stretta con le altre intestazioni di sicurezza, dichiarate una volta sola perché un `add_header` in una location le sostituirebbe. Il container rifiuta di partire senza l'origine delle API. Non avendo Docker in locale, ho fatto costruire e provare l'immagine vera alla CI a ogni push.

## Domande di autoverifica

1. **Perché serve il fallback in una SPA?**
   Perché le rotte esistono solo nel router del client. Ricaricando `/students`, il server deve restituire `index.html`, non un 404.

2. **Perché `index.html` non va in cache e i file in `/assets/` sì?**
   I file in `/assets/` hanno l'hash nel nome e non cambiano mai. `index.html` cambia a ogni deploy e punta ai file nuovi.

3. **Cosa succede se una `location` usa `add_header`?**
   Le intestazioni dichiarate a livello di server non valgono più per quella `location`: la CSP sparisce da quelle risposte.

4. **Perché il container rifiuta di partire senza `API_ORIGIN`?**
   Perché partirebbe con una CSP rotta e un portale che non può chiamare le API. Meglio un errore visibile al deploy.

5. **Come garantiamo che nessuno pubblichi una porta in futuro?**
   Con un test del backend che legge il compose di Coolify e fallisce se un servizio ha `ports`.
