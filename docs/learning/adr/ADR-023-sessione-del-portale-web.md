# ADR-023: La sessione del portale web e il refresh token in localStorage

- Stato: accettato
- Data: 2026-11-10

## Contesto

Dalla fase 4 il backend ruota i refresh token e mette nella lista nera quello appena usato (ADR-018). Il portale web, fermo all'MVP, al rinnovo salvava il nuovo token di accesso ma non il nuovo refresh token: al rinnovo successivo, dopo circa 30 minuti, usava un token bruciato e l'utente veniva disconnesso. In più faceva rinnovi in parallelo, il logout era solo locale, e salvava entrambi i token in `localStorage`.

## Decisione

- Dopo ogni rinnovo il portale salva **il refresh token ruotato**.
- **Un solo rinnovo alla volta.** Dentro una scheda, le richieste che ricevono 401 insieme condividono una promise. Tra schede, che condividono lo stesso `localStorage`, il rinnovo prende un Web Lock (`navigator.locks.request`) e rilegge il token salvato dentro il lock, perché un'altra scheda potrebbe averlo appena ruotato. Dove il browser non ha i Web Lock, resta la promise condivisa.
- Il **token di accesso sta solo in memoria**. Ricaricando la pagina si perde, e il portale ne chiede uno nuovo con il refresh token.
- Il **refresh token resta in `localStorage`**. È un rischio accettato, per decisione del proprietario del 10 novembre 2026: uno script iniettato nella pagina (XSS) potrebbe leggerlo. Lo mitigano la Content-Security-Policy stretta (ADR-025), la rotazione e la lista nera del backend, e il logout lato server.
- Il **logout** chiama `POST /auth/logout/`, riprova una volta con il token riletto se riceve 400 (un rinnovo appena prima può averlo ruotato) e poi svuota comunque token e cache.
- Al caricamento della pagina il portale chiede `GET /auth/me/`. Se il server non risponde, non disconnette l'utente.

## Alternative scartate

- **Refresh token in un cookie httpOnly**, illeggibile da JavaScript. È la soluzione migliore contro l'XSS ed è il **prossimo passo**. Richiede un endpoint del backend che imposti il cookie, la protezione CSRF per quel cookie e il CORS con credenziali. Rimandata per decisione del proprietario, per non cambiare il backend in questa fase.
- **Anche il token di accesso in `localStorage`**: più esposizione, nessun vantaggio.
- **BroadcastChannel** per sincronizzare le schede: più codice di un lock.

## Conseguenze

- Il bug delle disconnessioni è coperto da un test che, ripristinando il comportamento vecchio, fallisce.
- Una scheda aperta da giorni, se nel frattempo il refresh token è scaduto o revocato, porta al login con il messaggio "sessione terminata".
- Il rischio XSS sul refresh token è scritto qui e nel README del portale, perché chi fa la review lo veda.
