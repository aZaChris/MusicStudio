# Indice della documentazione di studio

Questa cartella è materiale di studio, in italiano. Ogni file si capisce da solo e si può caricare singolarmente in NotebookLM. Il codice, i commenti e i commit sono in inglese.

Stato: **fine della fase 3** (Celery e pagamenti), 6 novembre 2026.

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
20. `concetti/sicurezza-api-owasp.md` — la checklist OWASP, aggiornata a ogni fase.
21. Gli ADR, in ordine di numero.
22. `colloquio/domande-e-risposte.md` — per ripassare prima di un colloquio.
23. `glossario.md` — da consultare quando serve.

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
- `concetti/sicurezza-api-owasp.md` — OWASP API Top 10, stato alla fine della fase 2, rate limiting.

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

### Ripasso

- `glossario.md` — ogni termine tecnico in italiano semplice.
- `colloquio/domande-e-risposte.md` — 29 domande con risposta modello e punto debole.

## Formato dei documenti di concetto

Ogni documento in `concetti/` ha da 800 a 1500 parole e sempre le stesse sezioni: TL;DR; il problema reale; come funziona, con un'analogia; come lo abbiamo applicato in MusicStudio, con i percorsi dei file e il prima e dopo; alternative considerate; errori comuni e trade-off; come lo spiegheresti a un colloquio in 5 frasi; 5 domande di autoverifica con risposta.

## Prossime fasi (concetti previsti)

- **Fase 4, produzione**: osservabilità con Sentry e log strutturati, test di carico con Locust, deploy reale su Coolify, prova di ripristino dei backup.
- **Fase 5, rifinitura**.

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
