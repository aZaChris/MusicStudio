# KB: Il portale web disconnetteva gli utenti dopo circa 30 minuti

## Sintomo
Nessuna segnalazione: è emerso durante l'audit del portale web (10 novembre 2026). Contro il backend della fase 4, un utente del portale sarebbe stato rimandato al login dopo circa mezz'ora di uso, senza aver fatto logout.

## Causa radice
Dalla fase 4 il backend ruota i refresh token e mette nella lista nera quello appena usato (ADR-018). Il client del portale (`frontend/src/api/client.ts`), al rinnovo, salvava il nuovo token di accesso ma **non il nuovo refresh token**. Al rinnovo successivo, dopo circa 30 minuti, usava un refresh già bruciato: il server rispondeva 401 e la sessione finiva. In più il client faceva rinnovi in parallelo, e con la rotazione solo il primo riesce.

## Come l'abbiamo confermata
Lettura del client sapendo cosa era cambiato nel backend. Poi un test (`a 401 refreshes once, STORES THE ROTATED refresh token`) che, ripristinando il comportamento vecchio, fallisce.

## Risoluzione
Il refresh token ruotato viene salvato dopo ogni rinnovo; un solo rinnovo alla volta (promise condivisa nella scheda, Web Lock tra schede, token riletto dentro il lock); token di accesso solo in memoria; logout lato server. ADR-023.

## Lezione per il futuro
Quando il backend cambia il comportamento dell'autenticazione, va controllato ogni client, anche quelli "fuori perimetro". Un client fermo non è un client stabile: è un client che smette di funzionare in silenzio.

## Riferimenti
- `docs/learning/adr/ADR-023-sessione-del-portale-web.md`
- `docs/learning/audit-frontend.md`
- `frontend/src/api/client.test.ts`
