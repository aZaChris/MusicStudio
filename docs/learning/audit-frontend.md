# Audit iniziale del portale web (SPA in `frontend/`)

## TL;DR

Il portale web è una SPA React che parla con il backend Django. È ferma all'MVP (commit `4be062d`) e non ha seguito le fasi 1–4 del backend. Il problema più grave è un bug vero: da quando il backend ruota i refresh token (fase 4), la SPA disconnette gli utenti dopo circa 30 minuti. Mancano anche il logout lato server, la containerizzazione sicura per Coolify, i tipi generati dal contratto e la CI. Questo documento fotografa lo stato del 10 novembre 2026 ed è storico.

## Da dove partiamo

- React 19, TypeScript, Vite 8, TanStack Query, react-router 7, i18next, Vitest con Testing Library, oxlint.
- Circa 1.400 righe in `src/`: login, dashboard insegnante, elenco allievi, dettaglio allievo, pagamenti, portale genitore.
- Misurato all'inizio: TypeScript senza errori, ma con la modalità `strict` **non attivata** in `tsconfig.app.json` (attivandola, il codice compila comunque); oxlint 0 errori e 2 avvisi; build di produzione riuscita (JavaScript 374 kB, 116 kB compressi); 3 test, che passano, ma uno è fallito alla prima esecuzione a macchina appena avviata e poi è passato: da tenere d'occhio.
- Fino alla constitution 3.0.0 la cartella era "fuori perimetro, non modificare". Per questo non ha seguito le fasi del backend.

## Problemi trovati, in ordine di gravità

### Gravi

1. **Disconnessione dopo circa 30 minuti.** `src/api/client.ts`, al rinnovo, salva il nuovo token di accesso ma non il nuovo refresh token. Dalla fase 4 il backend mette nella lista nera il refresh appena usato. Il secondo rinnovo, dopo circa 30 minuti, usa un token già bruciato: il server rifiuta e l'utente viene disconnesso.
2. **Rinnovi paralleli.** Se più richieste ricevono 401 insieme, ognuna avvia un rinnovo con lo stesso refresh token. Con la rotazione, solo il primo riesce.
3. **Logout solo locale.** `logout()` cancella i token dal browser ma non chiama `POST /auth/logout/`: il refresh token resta valido sul server per 14 giorni. E non svuota la cache di React Query: sullo stesso browser il prossimo utente può vedere per un istante i dati del precedente.
4. **Non è pronta per Coolify.** Nel compose di produzione la SPA non c'è. Il `Dockerfile` esistente (`infra/frontend.Dockerfile`) usa `nginx:alpine` senza versione fissata, gira come root, non ha il fallback delle rotte (ricaricare `/students` dà 404) e non imposta intestazioni di sicurezza (CSP, protezione dagli iframe, `Referrer-Policy`). L'indirizzo delle API non è passato alla build.

### Medi

5. **Token in `localStorage`.** Sia il token di accesso sia il refresh token. Uno script iniettato nella pagina (XSS) li leggerebbe. Decisione del proprietario: per ora il refresh resta in `localStorage`, documentato in un ADR, con il cookie httpOnly come fase successiva. Il token di accesso, invece, può passare in memoria senza toccare il backend.
6. **Tipi scritti a mano.** Le interfacce in `src/features/*/api/*.ts` duplicano il contratto. Nel mobile, generare i tipi ha fatto emergere tre errori di contratto: qui il rischio è lo stesso.
7. **Solo la prima pagina.** Studenti e pagamenti leggono solo `results` della prima pagina: oltre 25 elementi, il resto sparisce.
8. **Nessuna CI** per la SPA: la pipeline controlla solo il backend.
9. **Pochi test**: 3, uno per schermata principale, senza casi di errore o di sessione.

### Minori

10. **README del template di Vite** e titolo della pagina `frontend`.
11. **Due avvisi di oxlint** (`only-export-components`) in `AuthProvider.tsx` e `ThemeProvider.tsx`.

## Cosa non è stato verificato all'inizio

Il comportamento con il backend vero e il deploy su Coolify: sono parte della fase.

## Piano

Feature `specs/006-web-spa-hardening`: sessione corretta (rotazione, un solo rinnovo, logout vero, cache svuotata, token di accesso in memoria), container sicuro per Coolify senza porte pubblicate, tipi generati dal contratto, tutte le pagine, errori visibili, test, CI, documentazione di studio.
