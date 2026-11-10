# Indice della documentazione di studio — app mobile

Questa cartella è materiale di studio in italiano sull'app mobile (branch `refactor/mobile`). Ogni file si capisce da solo e si può caricare singolarmente in NotebookLM. Il codice, i commenti e i commit sono in inglese. La documentazione del backend è sul branch `refactor/production-standards`.

Stato: **fine della fase 1 del mobile** (parità sulle API Django), 10 novembre 2026.

## Ordine di lettura consigliato

1. `audit-iniziale.md` — da dove siamo partiti e cosa non andava.
2. `concetti/client-api-generato-dal-contratto.md` — i tipi generati dal contratto OpenAPI.
3. `concetti/sessione-jwt-nel-client.md` — rinnovo con un solo refresh alla volta, logout vero.
4. `concetti/stato-del-server-con-react-query.md` — errori, retry, invalidazione, paginazione.
5. `concetti/test-di-un-app-react-native.md` — l'app vera con la rete finta.
6. `verifica-end-to-end.md` — la prova contro il backend Django vero.
7. `concetti/sicurezza-mobile-owasp.md` — la OWASP Mobile Top 10, voce per voce.
8. Gli ADR, in ordine: `adr/ADR-M001…M005`.
9. `colloquio/domande-e-risposte.md` — per ripassare.
10. `glossario.md` — da consultare quando serve.

## Decisioni (ADR)

- `adr/ADR-M001-refactor-dal-branch-app.md` — perché si parte dal branch `app`.
- `adr/ADR-M002-tipi-generati-dal-contratto.md` — contratto copiato, tipi generati, controllo in CI.
- `adr/ADR-M003-sessione-jwt-nel-client.md` — token in memoria e nel Keychain, single flight, logout.
- `adr/ADR-M004-errori-e-retry-con-react-query.md` — errori visibili, niente retry sui 4xx.
- `adr/ADR-M005-strategia-di-test.md` — Jest e RNTL con l'app vera e `fetch` finto.

## Riepilogo della fase 1

- **Backend nuovo:** l'app parla con le API Django: login con token di accesso e refresh a rotazione, `/auth/me/` all'avvio, logout che chiude la sessione sul server.
- **Contratto:** tipi generati dal contratto OpenAPI, controllo in CI; tre errori del contratto trovati e corretti sul backend.
- **Sessione:** un solo rinnovo alla volta, sessione mantenuta se si è offline, cache svuotata al cambio di utente, caso del logout con token scaduto corretto.
- **Schermate:** parità con il branch `app`, più gli errori visibili e tradotti, gli stati vuoti, tutte le pagine di studenti, le date locali, il logout per ogni ruolo, l'accessibilità.
- **Qualità:** da 0 a 53 test, ESLint pulito, CI su GitHub Actions, verifica end-to-end 9 su 9.
- **Aperto:** prova su un telefono vero con Expo Go; due vulnerabilità di `expo-router` nel bundle, in attesa di una patch dell'SDK; messaggi del server solo in inglese.
