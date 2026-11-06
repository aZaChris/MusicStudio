# ADR-001: Ripartire dal backend Django del commit 4be062d

- Stato: accettato
- Data: 2026-11-06

## Contesto

MusicStudio è stato costruito tre volte. Prima con Django, DRF e React (fino al commit `4be062d`). Poi riscritto in Next.js su Vercel (branch `web`). Infine è nata un'app Expo (branch `app`), che usa le API di Next.js.

Le nuove linee guida chiedono Django, DRF, PostgreSQL, Celery, Docker Compose e Coolify, senza AWS e senza Vercel. Chiedono anche di non ripartire da zero, ma di rivedere il progetto esistente.

Non esiste un branch `main`. Il branch di default su GitHub è `web`.

Bisogna scegliere da quale commit far partire il branch `refactor/production-standards`.

## Decisione

Il branch parte da `4be062d`, l'ultimo commit con il backend Django completo. A questo si aggiunge un solo commit che ignora i file locali lasciati dal branch `app`.

I branch `web` e `app` non vengono modificati.

## Alternative scartate

- **Partire da `app` e ripristinare `backend/` dalla storia.** Il branch `app` ha l'app Expo nella radice del repository (`src/`, `package.json`, `app.json`). Mescolare un progetto Expo e un progetto Django nella stessa radice confonde strumenti e lettori. Inoltre il frontend non va toccato, quindi non potrei nemmeno spostarlo in una sottocartella.
- **Partire da `web` e riscrivere il backend in Django.** È esattamente la riscrittura da zero che le linee guida vietano. Il codice Django esiste già, con 26 test verdi.
- **Restare su Next.js.** È incompatibile con lo stack richiesto.

## Conseguenze

- Recuperiamo modelli, migrazioni, test e artefatti spec-kit coerenti con Django.
- Il branch `refactor/production-standards` non condivide la storia recente di `web` e `app`. Un eventuale merge futuro andrà pianificato: probabilmente il backend diventerà la base, e l'app Expo verrà riadattata alle API Django.
- Non avendo un `main`, la regola "non toccare main" è rispettata per definizione. Quando creerai un `main` su GitHub, conviene crearlo da questo branch dopo la revisione, e attivare lì la branch protection.
- L'app Expo oggi chiama le API Next.js. Allinearla alle API Django è un lavoro esplicitamente fuori da questa fase.
