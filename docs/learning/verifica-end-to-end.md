# Verifica end-to-end contro il backend Django

Questo documento registra la prova dell'app contro il backend vero, non contro un finto. I test con Jest provano il codice dell'app con la rete simulata. Qui invece la build web dell'app parla con Django, che parla con PostgreSQL. Se il contratto, il CORS o la sessione non funzionano, è qui che si vede.

## Come è stata fatta

- **Data**: 10 novembre 2026.
- **Backend**: branch `refactor/production-standards`, server di sviluppo di Django sulla porta 8000, PostgreSQL 16 locale, dati creati da `manage.py seed_demo`, `CORS_ALLOWED_ORIGINS=http://localhost:8081`.
- **App**: build web esportata con `EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 npx expo export --platform web`, servita con `npx expo serve --port 8081`.
- **Guida**: lo script `scripts/verify-django.mjs`, che usa Playwright con Chromium. Ogni passo controlla l'interfaccia e, quando serve, chiede conferma direttamente alle API: per esempio che la lezione sia davvero completata nel database, non solo sparita dallo schermo.

## Risultato

```
PASS  opens on the login screen without a session
PASS  wrong password shows 'Invalid email or password.'
PASS  owner signs in and sees the server's dashboard counts
PASS  completing a lesson with a note updates the server and the home
PASS  roster lists students and the detail shows the completed lesson with its note
PASS  a cash payment is registered with today's local date
PASS  logout returns to login and the old refresh token is refused by the server
PASS  parent sees the read-only portal of the linked child
PASS  no uncaught errors in the page

9/9 steps passed
```

Il passo più importante per la sicurezza è il settimo. Prima del logout lo script legge il refresh token salvato. Dopo il logout lo rimanda al server, che risponde 401: il logout ha davvero chiuso la sessione sul backend, non solo sul telefono.

## Un problema trovato, e come l'abbiamo aggirato

Il primo tentativo è fallito: 3 passi su 9. Il login dall'app non arrivava mai alla home. Nel log di Django c'erano molti `TimeoutError` dai throttle.

Il motivo: su questa macchina Redis non è installato. I throttle "falliscono aperti" quando Redis è giù (ADR-017 del backend), ma prima aspettano il timeout di connessione. Ogni richiesta impiegava secondi in più, e l'interfaccia superava le attese dello script. Non è un difetto dell'app: è il costo, misurabile, della scelta fail open quando Redis non risponde subito.

Per la prova abbiamo usato un file di settings tenuto fuori dal repository. Parte dai settings di sviluppo e cambia solo la cache, che diventa in memoria. Con questa modifica, 9 passi su 9.

## Cosa non è stato verificato

- L'app su un telefono vero, con Expo Go. Su iOS e Android il refresh token sta nel Keychain o nel Keystore, non in `localStorage` come nella build web.
- Il backend in produzione su Coolify, con HTTPS e il proxy.

## Come ripeterla

I comandi sono in `specs/002-django-api-parity/quickstart.md` e in testa allo script. Senza Redis serve una cache in memoria, come spiegato sopra.
