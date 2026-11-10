# ADR-M003: Sessione JWT nel client con un solo refresh alla volta

- Stato: accettato
- Data: 2026-11-09

## Contesto

Il backend emette un token di accesso di 15 minuti e un refresh token di 14 giorni con rotazione: a ogni rinnovo il vecchio refresh finisce nella lista nera (ADR-018 del backend). L'app ereditata salvava un solo token, non lo rinnovava mai e faceva il logout solo sul telefono.

## Decisione

- Il **token di accesso** sta solo in memoria. Il **refresh token** sta in `expo-secure-store` (Keychain su iOS, Keystore su Android; sul web, solo per lo sviluppo, `localStorage`).
- Su un 401 il client rinnova e riprova **una** volta. Le richieste che ricevono 401 insieme aspettano **la stessa** promise di rinnovo: un solo refresh in volo.
- Se il rinnovo viene rifiutato, la sessione si cancella e il contesto di autenticazione porta l'utente al login con un messaggio. Se il server non è raggiungibile, la sessione resta.
- Il logout chiama `POST /auth/logout/`, poi cancella comunque lo stato locale e tutta la cache di React Query. Se il primo tentativo fallisce con 400 perché nel frattempo il token è ruotato, rilegge il token e riprova una volta.
- All'avvio l'app chiede `GET /auth/me/` invece di fidarsi di un utente salvato.
- Il client è un piccolo `apiFetch` scritto da noi, tipizzato con i tipi generati.

## Alternative scartate

- **Rinnovi paralleli**: il secondo userebbe un refresh appena messo nella lista nera, e l'utente verrebbe disconnesso a caso.
- **openapi-fetch con un middleware, o axios con un interceptor**: una dipendenza in più per circa 80 righe; rimandare una richiesta da un middleware, con il corpo già consumato, è scomodo.
- **Salvare anche il token di accesso**: nessun vantaggio, scade in 15 minuti.

## Conseguenze

- Test dedicati: tre richieste con token scaduto producono un solo refresh; togliendo la promise condivisa il test fallisce con tre refresh.
- Il caso del logout con token scaduto è coperto da un test che fallisce senza il secondo tentativo.
