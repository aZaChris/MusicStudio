# Indice della documentazione di studio

Questa cartella è materiale di studio, in italiano. Ogni file si capisce da solo e si può caricare singolarmente in NotebookLM. Il codice, i commenti e i commit sono in inglese.

Stato: **fine della fase 1** (fondamenta e allineamento), 6 novembre 2026.

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
12. `concetti/sicurezza-api-owasp.md` — la checklist OWASP di fine fase.
13. Gli ADR, in ordine di numero.
14. `colloquio/domande-e-risposte.md` — per ripassare prima di un colloquio.
15. `glossario.md` — da consultare quando serve.

Se hai poco tempo, leggi per primi: la panoramica, l'audit, il documento su BOLA e le domande da colloquio.

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
- `adr/ADR-008-promemoria-at-most-once.md` — promemoria senza duplicati, con il loro limite.

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
- `concetti/sicurezza-api-owasp.md` — OWASP API Top 10, stato alla fine della fase 1, rate limiting.

### Ripasso

- `glossario.md` — ogni termine tecnico in italiano semplice.
- `colloquio/domande-e-risposte.md` — 19 domande con risposta modello e punto debole.

## Formato dei documenti di concetto

Ogni documento in `concetti/` ha da 800 a 1500 parole e sempre le stesse sezioni: TL;DR; il problema reale; come funziona, con un'analogia; come lo abbiamo applicato in MusicStudio, con i percorsi dei file e il prima e dopo; alternative considerate; errori comuni e trade-off; come lo spiegheresti a un colloquio in 5 frasi; 5 domande di autoverifica con risposta.

## Prossime fasi (concetti previsti)

- **Fase 2, dominio**: ExclusionConstraint contro le sovrapposizioni, multi-tenancy, permessi DRF, OpenAPI.
- **Fase 3, Celery e pagamenti**: task Celery idempotenti, webhook idempotenti con Stripe in modalità test, caching.
- **Fase 4, produzione**: osservabilità con Sentry e log strutturati, test di carico con Locust, deploy reale su Coolify, prova di ripristino dei backup.
- **Fase 5, rifinitura**.

Il dettaglio è in `specs/002-production-foundations/plan.md`, sezione "Roadmap".
