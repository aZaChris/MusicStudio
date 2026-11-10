# ADR-M005: Test con l'app vera e la rete finta

- Stato: accettato
- Data: 2026-11-09

## Contesto

L'app ereditata non aveva nessun test. Non ci sono emulatori iOS o Android nell'ambiente di lavoro.

## Decisione

- **Jest con `jest-expo`** e **React Native Testing Library 14**.
- Si renderizza l'**app vera**, con `renderRouter("./src/app")` di Expo Router: layout, provider, autenticazione e schermate reali. L'unica cosa finta è `fetch`, sostituito da un piccolo router di risposte (`src/test/fake-api.ts`). `expo-secure-store` è sostituito da una mappa in memoria.
- I test girano con `TZ=Europe/Rome`, così gli errori sulle date si vedono come li vedrebbero gli utenti.
- In più, una verifica end-to-end della build web contro il backend Django vero, con Playwright (`scripts/verify-django.mjs`).

## Alternative scartate

- **Mock dei moduli interni** (per esempio del client): si testerebbe il mock, non il rinnovo della sessione o la gestione degli errori.
- **MSW**: un'altra dipendenza, con polyfill in React Native, per una dozzina di rotte.
- **Detox o Maestro**: servono emulatori.

## Conseguenze

- RNTL 14 ha `render` e `fireEvent` asincroni: vanno sempre aspettati con `await`.
- Con l'app intera in ogni test e più worker in parallelo, i timeout predefiniti non bastavano su una macchina da 2,7 GB: alzati a 5 secondi per le attese e 30 per test.
- Per tre test importanti abbiamo verificato che falliscano davvero togliendo il codice che li protegge.
