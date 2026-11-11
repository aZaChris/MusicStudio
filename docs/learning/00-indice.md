# Indice della documentazione di studio

Questa cartella è materiale di studio, in italiano. Ogni file si capisce da solo e si può caricare singolarmente in NotebookLM. Il codice, i commenti e i commit sono in inglese.

Stato: **fine della fase 4** (produzione) e del **Web 1** (portale web), 10 novembre 2026.

## Ordine di lettura consigliato

1. `01-panoramica-architettura.md` — il sistema dall'alto e il perché di ogni scelta di stack.
2. `audit-iniziale.md` — da dove siamo partiti: cosa andava, cosa no, e i difetti trovati.
3. `concetti/isolamento-tenant-e-bola.md` — la falla più grave trovata e come è stata chiusa.
4. `concetti/service-layer-e-modular-monolith.md` — come è organizzato il codice.
5. `concetti/orm-e-problema-n-piu-1.md` — perché le liste facevano troppe query.
6. `concetti/indici-ed-explain.md` — indici misurati con EXPLAIN ANALYZE.
7. `concetti/strategia-di-test.md` — cosa testiamo e perché.
8. `concetti/configurazione-per-ambienti.md` — settings, variabili d'ambiente, proxy TLS.
9. `concetti/docker-e-deploy-con-coolify.md` — immagine, Compose e Coolify.
10. `concetti/health-check-e-backup.md` — liveness, readiness e backup.
11. `concetti/ci-e-quality-gate.md` — la pipeline che blocca il codice difettoso.
12. `concetti/multi-tenancy.md` — lo studio come tenant (fase 2).
13. `concetti/exclusion-constraint.md` — niente lezioni sovrapposte, anche in concorrenza (fase 2).
14. `concetti/permessi-drf.md` — permessi per azione e per oggetto (fase 2).
15. `concetti/openapi-e-contratti.md` — il contratto API versionato (fase 2).
16. `concetti/pagamenti-online-stripe.md` — Stripe Checkout in modalità test (fase 3).
17. `concetti/webhook-idempotenti.md` — notifiche verificate, salvate una volta, elaborate in background (fase 3).
18. `concetti/task-celery-idempotenti.md` — acks late, idempotenza, outbox dei promemoria (fase 3).
19. `concetti/caching.md` — chiavi versionate e il guasto di Redis (fase 3).
20. `concetti/revoca-token-jwt.md` — logout vero, rotazione e lista nera (fase 4).
21. `concetti/ip-reale-dietro-proxy.md` — X-Forwarded-For e il bug del limite sul login (fase 4).
22. `concetti/log-strutturati-e-sentry.md` — request id, log JSON, Sentry senza dati personali (fase 4).
23. `concetti/backup-off-site-e-restore-drill.md` — copie cifrate fuori dal server e prova di ripristino (fase 4).
24. `concetti/load-testing.md` — Locust, percentili e il costo del login (fase 4).
25. `audit-frontend.md` — il portale web all'inizio del Web 1: il bug delle disconnessioni e il resto.
26. `concetti/sicurezza-di-una-spa.md` — XSS, Content-Security-Policy, token nel browser (Web 1).
27. `concetti/deploy-di-una-spa-con-nginx.md` — fallback, cache, intestazioni, niente porte esposte (Web 1).
28. `verifica-web-end-to-end.md` — il portale contro il backend vero.
29. `concetti/sicurezza-api-owasp.md` — la checklist OWASP, aggiornata a ogni fase.
30. Gli ADR, in ordine di numero.
31. `../operations/runbook.md` — deploy, rollback, segreti, ripristino.
32. `colloquio/domande-e-risposte.md` — per ripassare prima di un colloquio.
33. `glossario.md` — da consultare quando serve.

Se hai poco tempo, leggi per primi: la panoramica, l'audit, il documento su BOLA, quello sull'ExclusionConstraint e le domande da colloquio.

## Mappa dei documenti

### Visione d'insieme

- `01-panoramica-architettura.md` — architettura, scelte di stack e limiti dichiarati.
- `audit-iniziale.md` — stato del repository all'inizio, gap analysis con gravità, problemi emersi durante il lavoro.

### Decisioni (ADR)

- `adr/ADR-001-punto-di-partenza-backend-django.md` — perché il lavoro riparte dal commit Django `4be062d`.
- `adr/ADR-002-modular-monolith-e-service-layer.md` — un'app per dominio, service e selector.
- `adr/ADR-003-coolify-al-posto-di-aws.md` — Docker Compose su Coolify, nessuna porta pubblicata.
- `adr/ADR-004-configurazione-per-ambienti.md` — settings per ambiente, produzione fail-fast.
- `adr/ADR-005-backup-postgres-con-sidecar.md` — pg_dump giornaliero con rotazione.
- `adr/ADR-006-health-endpoint-live-e-ready.md` — due controlli di salute separati.
- `adr/ADR-007-ci-github-actions.md` — la pipeline di qualità.
- `adr/ADR-008-promemoria-at-most-once.md` — promemoria senza duplicati, con il loro limite (sostituito da ADR-015).
- `adr/ADR-009-exclusion-constraint-per-le-sovrapposizioni.md` — il database vieta le lezioni sovrapposte.
- `adr/ADR-010-studio-come-tenant.md` — lo studio obbligatorio per insegnanti e allievi.
- `adr/ADR-011-permessi-per-oggetto.md` — permessi per oggetto, spostamento allievi, limite insegnanti.
- `adr/ADR-012-contratto-openapi-versionato.md` — lo schema OpenAPI nel repository, controllato in CI.
- `adr/ADR-013-pagamenti-online-stripe-checkout.md` — Stripe Checkout, solo modalità test.
- `adr/ADR-014-webhook-salvati-poi-elaborati.md` — verifica, salva una volta, elabora in background.
- `adr/ADR-015-outbox-per-i-promemoria.md` — promemoria affidabili con una outbox.
- `adr/ADR-016-affidabilita-celery.md` — acks late e task idempotenti.
- `adr/ADR-017-cache-dashboard-con-versioni.md` — cache con chiavi versionate e throttling fail open.
- `adr/ADR-018-revoca-dei-token.md` — lista nera dei refresh token, logout, token di accesso da 15 minuti.
- `adr/ADR-019-osservabilita-log-e-sentry.md` — request id, log JSON, Sentry ripulito.
- `adr/ADR-020-backup-off-site.md` — rclone crypt con `copy`, prova di ripristino.
- `adr/ADR-021-allowlist-webhook-e-ip-reale.md` — IP di Stripe e IP reale dietro il proxy.
- `adr/ADR-022-load-test-con-locust.md` — Locust in un gruppo separato, baseline documentato.
- `adr/ADR-023-sessione-del-portale-web.md` — refresh ruotato salvato, un solo rinnovo, refresh in localStorage come rischio accettato.
- `adr/ADR-024-tipi-del-portale-dal-contratto.md` — tipi del portale generati da `backend/openapi.yaml`.
- `adr/ADR-025-container-del-portale.md` — nginx senza privilegi, niente porte, intestazioni di sicurezza, prova in CI.
- `adr/ADR-026-backup-gestiti-dal-server.md` — i backup li fa chi amministra il server; i servizi dello stack diventano opzionali.
- `adr/ADR-027-principi-sicurezza-e-privacy.md` — il principio X della constitution; PBKDF2 resta, Argon2 come miglioramento.
- `adr/ADR-028-link-senza-tabella.md` — link di conferma e reset firmati, a uso singolo senza tabella.
- `adr/ADR-029-mfa-totp-con-la-libreria-standard.md` — TOTP in quaranta righe, vettori ufficiali, codici di recupero.
- `adr/ADR-030-cifratura-dei-campi.md` — Fernet, MultiFernet e rotazione delle chiavi.
- `adr/ADR-031-audit-log-dai-service.md` — registro append-only scritto dai service.
- `adr/ADR-032-cancellazione-come-anonimizzazione.md` — anonimizzare sul posto e tempi di conservazione.

### Concetti (fase 1)

- `concetti/service-layer-e-modular-monolith.md` — dove vive la logica di business.
- `concetti/orm-e-problema-n-piu-1.md` — select_related, prefetch, subquery e budget di query.
- `concetti/indici-ed-explain.md` — indici composti e parziali, misurati.
- `concetti/isolamento-tenant-e-bola.md` — autorizzazione a livello di oggetto, in lettura e in scrittura.
- `concetti/configurazione-per-ambienti.md` — Twelve-Factor, fail fast, proxy TLS.
- `concetti/strategia-di-test.md` — pytest, factory_boy, PostgreSQL vero, copertura.
- `concetti/ci-e-quality-gate.md` — GitHub Actions, pre-commit, branch protection.
- `concetti/docker-e-deploy-con-coolify.md` — multi-stage, entrypoint, Compose per Coolify.
- `concetti/health-check-e-backup.md` — probe, RPO, rotazione dei backup.
- `concetti/sicurezza-api-owasp.md` — OWASP API Top 10, stato aggiornato alla fine della fase 4.

### Concetti (fase 2)

- `concetti/exclusion-constraint.md` — vincoli di esclusione, range di tempo, deadlock e fusi orari.
- `concetti/multi-tenancy.md` — modelli di multi-tenancy, contesto per richiesta, migrazione.
- `concetti/permessi-drf.md` — has_permission, has_object_permission, regole di prodotto.
- `concetti/openapi-e-contratti.md` — code-first con schema versionato, tag, errori documentati.

### Concetti (fase 3)

- `concetti/pagamenti-online-stripe.md` — Checkout Session, chiavi ristrette, idempotency key, modalità test.
- `concetti/webhook-idempotenti.md` — firma HMAC, deduplica per id, elaborazione in background, riconciliazione.
- `concetti/task-celery-idempotenti.md` — acks late, retry con backoff, outbox e lease.
- `concetti/caching.md` — cache-aside, chiavi versionate, invalidazione con i segnali, fail open.

### Concetti (fase 4)

- `concetti/revoca-token-jwt.md` — rotazione, lista nera, logout, revoca di tutte le sessioni.
- `concetti/ip-reale-dietro-proxy.md` — contare da destra in X-Forwarded-For, `NUM_PROXIES` di DRF.
- `concetti/log-strutturati-e-sentry.md` — ContextVar, log JSON, propagazione a Celery, `before_send`.
- `concetti/backup-off-site-e-restore-drill.md` — off-site cifrato, `copy` contro `sync`, RPO e RTO.
- `concetti/load-testing.md` — utenti virtuali, percentili, PBKDF2, errori di misura.

### Concetti (Web 1, portale web)

- `concetti/sicurezza-di-una-spa.md` — XSS, CSP, dove tenere i token nel browser.
- `concetti/deploy-di-una-spa-con-nginx.md` — fallback delle rotte, cache, intestazioni, utente non root.

### Concetti (fase 7)

- `concetti/account-e-token-monouso.md` — risposte uguali, link a uso singolo, inviti con hash, blocco dell'account.
- `concetti/mfa-totp.md` — il codice a sei cifre, perché non si riusa, codici di recupero.
- `concetti/cifratura-dei-campi.md` — Fernet, rotazione delle chiavi, cosa non si può cercare.
- `concetti/gdpr-per-sviluppatori.md` — consenso, esportazione, cancellazione per anonimizzazione, conservazione.
- `concetti/audit-log.md` — chi ha fatto cosa, voci che non si riscrivono.

### Bozze legali (da validare)

- `../privacy/registro-trattamenti.md`, `../privacy/informativa-famiglie.md`, `../privacy/informativa-insegnanti.md`.

### Operazioni


- `../operations/runbook.md` — primo deploy, verifiche, rollback, rotazione dei segreti, Sentry, backup off-site, ripristino.
- `../operations/restore-drill.md` — registro delle prove di ripristino.
- `../loadtest/2026-11-09/README.md` — il primo baseline del load test.

### Ripasso

- `glossario.md` — ogni termine tecnico in italiano semplice.
- `colloquio/domande-e-risposte.md` — 42 domande con risposta modello e punto debole.

## Formato dei documenti di concetto

Ogni documento in `concetti/` ha da 800 a 1500 parole e sempre le stesse sezioni: TL;DR; il problema reale; come funziona, con un'analogia; come lo abbiamo applicato in MusicStudio, con i percorsi dei file e il prima e dopo; alternative considerate; errori comuni e trade-off; come lo spiegheresti a un colloquio in 5 frasi; 5 domande di autoverifica con risposta.

## Prossime fasi (concetti previsti)

- **Fase 5, rifinitura**: versioning e deprecazione delle API, rafforzamento dell'admin, presentazione del progetto per il portfolio. L'export dei dati (GDPR) è stato anticipato nella fase 7.

Il dettaglio è in `specs/002-production-foundations/plan.md`, sezione "Roadmap".

## Riepilogo della fase 1

- **Sicurezza:** chiuse le scritture cross-tenant (BOLA) e la fuga degli insegnanti solisti; rate limiting sul login; produzione che non parte senza segreti; checklist OWASP registrata.
- **Codice:** logica spostata in `services.py` e `selectors.py`; Django 5.2 LTS; mypy rigoroso sul codice di produzione.
- **Performance:** query costanti sugli endpoint principali (allievi da 2+2N a 4, dashboard da 5+N a 6); indici composti e parziali misurati con EXPLAIN.
- **Correttezza:** creazione dei pacchetti, settimana non valida (400), doppia scalatura concorrente, pacchetto di un altro allievo, promemoria at-most-once, `seed_demo` idempotente.
- **Operazioni:** settings per ambiente, health live e ready, Dockerfile multi-stage non root, Compose di sviluppo e per Coolify con healthcheck ovunque e backup giornaliero, AWS rimosso.
- **Qualità:** da 26 a 92 test, copertura 96%, CI su GitHub Actions, pre-commit.
- **Aperto:** primo `docker compose up` reale, branch protection su GitHub, copia off-site e prova di ripristino dei backup, revoca dei token.

## Riepilogo della fase 2

- **Agenda:** due vincoli di esclusione di PostgreSQL vietano lezioni sovrapposte per insegnante e per allievo, anche con richieste simultanee; 409 con messaggio chiaro; l'API mantiene `duration_minutes`.
- **Tenant:** lo studio è obbligatorio per insegnanti e allievi (studio personale per i solisti, via migrazione); contesto del tenant calcolato una volta per richiesta.
- **Permessi:** permesso per oggetto, spostamento degli allievi riservato al titolare, limite di 10 insegnanti protetto dalla concorrenza.
- **Pagamenti:** macchina a stati, «pagato» è finale.
- **Contratto:** `backend/openapi.yaml` nel repository, tag per dominio, errori documentati, controllo in CI.
- **Bug trovati dai test:** durata sbagliata la notte del cambio d'ora; deadlock tra prenotazioni simultanee.
- **Aperto:** coerenza studio allievo/insegnante garantita solo dai service; Row Level Security da valutare; tutto ciò che era aperto alla fase 1 (Docker reale, branch protection, backup off-site, revoca dei token).

## Riepilogo della fase 3

- **Pagamenti online:** Stripe Checkout in modalità test (chiavi live rifiutate all'avvio); un doppio clic riusa lo stesso tentativo; il pagamento si registra solo dal webhook.
- **Webhook:** firma verificata sul corpo grezzo, evento salvato una volta per id, elaborazione idempotente in Celery, un pagamento per tentativo garantito dal database, riconciliazione oraria.
- **Promemoria:** outbox con retry e lease; da "al massimo una volta" a "almeno una volta" senza doppioni.
- **Celery:** acks late, riconsegna dei task di un worker morto, prefetch 1, limiti di tempo, impostazioni fissate da un test.
- **Cache:** dashboard in cache con chiavi versionate per studio, invalidate dai segnali; da 6 query a 1.
- **Bug trovato dai test:** con Redis giù il rate limiting faceva cadere tutta l'API; ora fallisce aperto.
- **Aperto:** prova end-to-end con una sandbox Stripe reale; allowlist IP di Stripe; tutto ciò che era aperto prima (Docker reale, branch protection, backup off-site, revoca dei token).

## Riepilogo della fase 4

- **Autenticazione:** logout vero con la lista nera dei refresh token, rotazione che spegne il token usato, revoca di tutte le sessioni di un account da comando o admin, token di accesso da 15 minuti, pulizia giornaliera.
- **Bug trovato nel giro OWASP:** il limite sui tentativi di login si aggirava cambiando `X-Forwarded-For`, perché DRF senza `NUM_PROXIES` usava tutto l'header. Corretto, con un test che prova l'attacco.
- **Osservabilità:** request id in ogni riga di log e nei task Celery, log JSON in produzione, Sentry opzionale e ripulito da credenziali ed email. Provando con gunicorn vero è emerso che la riga di errore di Django perdeva l'id: corretto.
- **Deploy:** `check --deploy` in CI, variabili nuove nel Compose di Coolify, runbook in italiano.
- **Webhook Stripe:** allowlist degli IP con l'IP reale calcolato dietro il proxy.
- **Backup:** copia giornaliera cifrata fuori dal server con rclone (`copy`, non `sync`); prova di ripristino eseguita su 78.000 lezioni: 87.254 righe identiche, 20 secondi.
- **Load test:** Locust con 50 utenti, zero errori, p95 delle letture tra 62 e 560 ms su un portatile; il login è limitato dalla CPU (PBKDF2).
- **Qualità:** da 171 a 219 test, copertura 96%.
- **Aperto (serve il proprietario):** deploy reale su Coolify e misura del rollback; DSN di Sentry; bucket e prova di ripristino dal bucket vero; load test sul server; branch protection su GitHub. Restano anche la prova end-to-end con una sandbox Stripe reale e la coerenza dello studio garantita solo dai service.

## Riepilogo del Web 1 (portale web)

- **Perimetro riaperto:** constitution 3.0.0, il portale in `frontend/` si sviluppa su questo branch con gli stessi standard del backend.
- **Bug grave corretto:** dalla fase 4 il portale disconnetteva gli utenti dopo circa 30 minuti, perché non salvava il refresh token ruotato. Ora lo salva; un solo rinnovo alla volta, anche tra schede; logout vero con cache svuotata; token di accesso solo in memoria.
- **Dati:** tipi generati dal contratto, tutte le pagine di studenti e pagamenti, errori tradotti e mai ritentati sui 4xx, date locali (il form dei pagamenti usava il giorno UTC).
- **Deploy:** immagine con versioni fissate, nginx senza privilegi, fallback delle rotte, CSP stretta e altre intestazioni, nessuna porta pubblicata, CORS limitato al portale; un test vieta le porte nel compose, un job della CI prova l'immagine vera.
- **Qualità:** TypeScript strict attivato, oxlint senza avvisi, Prettier, da 3 a 48 test, CI dedicata, README per la review, verifica end-to-end 10 su 10.
- **Dopo la review (10 novembre):** l'amico ha approvato tutto tranne i backup, che gestisce lui sul suo server: i servizi di backup sono diventati opzionali (ADR-026). Il primo deploy avverrà su un dominio di staging.
- **Aperto (serve il proprietario):** deploy in staging; prova dell'immagine in locale quando Docker sarà attivo in WSL; refresh token in cookie httpOnly come passo successivo.

## Riepilogo della fase 7 (sicurezza, privacy e account)

- **Prova prima di cambiare:** una suite IDOR di 322 casi su ogni endpoint non ha trovato falle; un test di guardia fallisce se una rotta nuova non è coperta.
- **Account:** registrazione con conferma email, reset della password e cambio password che chiudono le sessioni, inviti per insegnanti, genitori e studenti adulti, ruolo studente in sola lettura, risposte che non rivelano se un'email esiste.
- **Accesso:** blocco progressivo dopo cinque password sbagliate, verifica in due passaggi TOTP (circa quaranta righe, vettori ufficiali) per titolari e insegnanti, comandi per l'operatore (`unlock_account`, `reset_mfa`).
- **Dati:** note delle lezioni e segreto TOTP cifrati con Fernet e chiavi ruotabili; registro delle azioni per il titolare; esportazione e cancellazione per le famiglie (anonimizzazione sul posto); conservazione automatica ogni notte.
- **Bug trovato dai test:** Celery scriveva il token d'invito nei log; corretto con un filtro (knowledge base).
- **CI:** il passo `check --deploy` mancava delle variabili nuove; corretto. Nuovo job con gitleaks sulla cronologia.
- **Qualità:** 740 test del backend, copertura circa 96%, ruff, mypy, migrazioni e contratto OpenAPI verdi.
- **Aperto:** le schermate del portale ancora mancanti (cambio password, squadra e inviti, impostazione dell'MFA, privacy, area studente, registro delle azioni: T023, T029, T035, T041, T043, T046) e il passo finale della fase; la scansione gitleaks mai eseguita in locale; le bozze legali da far validare (T057); la prova delle email con un fornitore SMTP vero (T058); l'app mobile (nota in `specs/007-security-privacy-accounts/mobile-followup.md`).

