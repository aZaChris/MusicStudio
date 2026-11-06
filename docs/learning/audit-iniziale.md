# Audit iniziale di MusicStudio

Data: 6 novembre 2026. Branch di lavoro: `refactor/production-standards`.

## TL;DR

Il backend Django esistente è una buona base. Ha già app separate per dominio, isolamento dei dati per ruolo e 26 test verdi su PostgreSQL. Però non è ancora "da produzione". Ci sono una falla di sicurezza reale (un insegnante può scrivere dati sugli allievi di un altro insegnante), due problemi N+1 misurati, nessuna CI, nessun type checking, deploy pensato per AWS e Django 5.1 fuori supporto. La raccomandazione è **correggere, non riscrivere**: ogni problema ha una correzione locale che costa poco.

## 1. Da dove partiamo: la storia del repository

Questo è il punto più importante dell'audit, perché cambia cosa intendiamo per "progetto esistente".

Il repository ha avuto tre vite:

1. **Django + DRF + React (Vite)**. Commit da `481ea4a` a `4be062d`. È stato costruito con spec-kit (feature `001-musicstudio-mvp`), con constitution, spec, piano e 56 task.
2. **Next.js su Vercel**. Il commit `c111eac` ha cancellato tutto lo stack Django e Docker. Il codice è stato riscritto in TypeScript con Drizzle e Neon Postgres. Vive nel branch `web`.
3. **App React Native (Expo)**. Il branch `app` parte dal branch `web`, toglie il codice web e crea un'app mobile che usa le API `/api/v1/` di Next.js.

Non esiste un branch `main`, né in locale né su GitHub. Il branch di default su GitHub è `web`.

Le nuove linee guida chiedono Django, DRF, Celery, PostgreSQL e Docker. Quello stack esiste già, nel commit `4be062d`. Per questo il branch `refactor/production-standards` parte da `4be062d` e non da `web` o `app`. La motivazione completa è nell'ADR-001 (`docs/learning/adr/ADR-001-punto-di-partenza-backend-django.md`).

I branch `web` e `app` non vengono toccati. Restano come sono, consultabili.

## 2. Struttura attuale (al commit 4be062d)

```text
backend/            progetto Django (uv, pyproject.toml)
  config/           settings base/dev/prod, urls, celery, wsgi/asgi
  apps/
    accounts/       User custom (email come login, campo role)
    studios/        Studio, Teacher
    students/       Student, ParentAccount, ParentStudentLink
    packages/       Package (pacchetti di lezioni prepagate)
    lessons/        Lesson, dashboard dell'insegnante
    payments/       Payment (registrazione manuale)
    notifications/  task Celery dei promemoria via email
    common/         permessi, factory dei test, comando seed_demo
frontend/           SPA React + Vite + TypeScript (fuori scope)
infra/              docker-compose.yml, Dockerfile, .env.example, docs AWS
specs/              artefatti spec-kit della feature 001
.specify/           constitution e template di spec-kit
design/             artboard di design e token
```

### Modelli

- `accounts.User`: estende `AbstractUser`. Login con email. Ruolo: `teacher`, `studio_owner`, `parent`. Lingua preferita EN/IT.
- `studios.Studio` e `studios.Teacher`: un insegnante può essere solo o far parte di uno studio. `Studio.owner` è un OneToOne verso Teacher.
- `students.Student`: appartiene a un insegnante. `ParentAccount` è collegato agli allievi tramite la tabella `ParentStudentLink` (vincolo di unicità sulla coppia).
- `packages.Package`: pacchetto di N lezioni. Ha un `CheckConstraint` che tiene `lessons_remaining` tra 0 e `total_lessons`. Lo stato (attivo, scaduto, completato) è calcolato, non salvato.
- `lessons.Lesson`: lezione con stato, durata, pacchetto opzionale e `reminder_sent_at` per i promemoria.
- `payments.Payment`: pagamento manuale (contanti, bonifico, inserimento manuale) con stato pagato, in attesa o scaduto.

### Endpoint (tutti sotto `/api/v1/`)

- `auth/token/`, `auth/token/refresh/`, `auth/me/`: autenticazione JWT (simplejwt).
- `studio/`, `studio/teachers/`: solo per il titolare dello studio.
- `students/` (CRUD) e `students/{id}/lessons/`.
- `packages/` (CRUD).
- `lessons/` (CRUD, filtrato per settimana), `lessons/upcoming/`, `lessons/{id}/complete/`, `lessons/{id}/cancel/`.
- `payments/` (CRUD).
- `dashboard/`: riepilogo della settimana per l'insegnante.
- `/api/schema/` e `/api/docs/`: OpenAPI con drf-spectacular.
- `/admin/`: admin di Django.

### Test esistenti

26 test con pytest, pytest-django e factory_boy. Coprono: la scalatura del pacchetto quando si completa una lezione (anche l'idempotenza), i permessi tra insegnanti, l'isolamento dei genitori, la validazione dei pagamenti e lo sweep dei promemoria. **Tutti passano su PostgreSQL 16** (verificato all'inizio di questo lavoro). Non ci sono test per health check, endpoint dello studio, `me`, dashboard, numero di query, né misura della copertura.

### Dipendenze

Django 5.1.15, DRF 3.17.2, simplejwt, drf-spectacular 0.30, django-filter, django-cors-headers, django-environ, Celery 5.6, redis, psycopg 3, gunicorn. Dev: pytest, pytest-django, factory-boy, ruff. Gestite con `uv` e `uv.lock`.

### Docker e CI

- `infra/docker-compose.yml`: db, redis, backend (runserver), celery-worker, celery-beat, frontend. Porte pubblicate sull'host (5432, 6379, 8000, 5173). Healthcheck solo su db.
- `infra/backend.Dockerfile`: immagine singola, gira come root, nessun healthcheck, `uv:latest` non fissato.
- **Nessuna CI**. Nessun pre-commit.
- `infra/aws/README.md`: guida di deploy su ECS Fargate, RDS, ElastiCache, ECR, Route 53.

## 3. Cosa rispetta già le regole

- **App separate per dominio.** È già un modular monolith in forma embrionale.
- **Isolamento in lettura.** Tutte le ViewSet filtrano il queryset per ruolo con `role_scoped_queryset` (`backend/apps/common/permissions.py`). Un oggetto di un altro tenant restituisce 404, non 403. Questo è corretto, perché non rivela che l'oggetto esiste.
- **Test con factory_boy** su un database PostgreSQL vero, non su SQLite.
- **Configurazione da variabili d'ambiente** con django-environ. `SECRET_KEY` è obbligatoria, non ha un default.
- **Nessun segreto nel codice.** Il file `infra/.env.example` contiene solo segnaposto.
- **OpenAPI** generato con drf-spectacular, senza warning.
- **Idempotenza** della scalatura del pacchetto: `select_for_update` sul pacchetto e controllo dello stato.
- **Vincoli nel database**: `CheckConstraint` sul pacchetto e `UniqueConstraint` sul collegamento genitore-allievo.
- **ruff** è configurato e pulito. Le migrazioni sono allineate ai modelli.

## 4. Gap analysis e problemi concreti

Per ogni problema indico la gravità (critica, alta, media, bassa), l'intervento e la scelta tra correggere e riscrivere.

### G1. Scrittura cross-tenant (BOLA). Gravità: critica

**Cosa succede.** I serializer di `Lesson`, `Payment` e `Package` accettano il campo `student` come id numerico. Il queryset di validazione è `Student.objects.all()`. Quindi un insegnante può creare una lezione o un pagamento sull'allievo di **un altro** insegnante.

**Come l'ho verificato.** Con un test temporaneo: un insegnante A fa POST su `/api/v1/lessons/` e `/api/v1/payments/` con l'id di un allievo dell'insegnante B. Risposta: **201 Created** in tutti e due i casi. Il dato finisce davvero nel tenant di B.

**Perché i test esistenti non lo vedevano.** I test di permesso controllano solo letture e azioni su oggetti esistenti (`complete`). L'isolamento era stato applicato al queryset della view, ma non ai campi di relazione del serializer. È la categoria OWASP API1 (Broken Object Level Authorization).

**Intervento.** Restringere i queryset dei campi di relazione (`student`, `package`) agli oggetti visibili all'utente. Aggiungere test di regressione per ogni endpoint di scrittura. **Correggere.**

### G2. Query N+1 su `/students/` e `/dashboard/`. Gravità: alta

**Misurato.** `/api/v1/students/` fa 4 query con 1 allievo e **22 query con 10 allievi**: due query in più per ogni allievo. La causa è nello `StudentSerializer`: `active_package` è una property del modello che fa una query, e `get_payment_status` ne fa un'altra. `/api/v1/dashboard/` passa da 5 a **14 query**, perché la lista degli allievi con pacchetto in esaurimento chiama `active_package` in un ciclo Python. Anche `StudioSerializer.teacher_count` fa una query `COUNT` dedicata e il task dei promemoria fa una query per ogni lezione.

**Intervento.** Selectors con `Prefetch` e `Subquery`/annotazioni. Test con `django_assert_num_queries` su tutti gli endpoint di lista principali, per bloccare le regressioni. **Correggere.**

### G3. Logica di business nei modelli, nelle view e nei serializer. Gravità: alta

**Cosa succede.** La logica è sparsa. `Lesson.mark_completed` e `Lesson.cancel` sono nel modello. Il calcolo della dashboard (4 query e un filtro Python) è dentro `DashboardView.get`. La scelta del pacchetto di default di una lezione è in `LessonSerializer.create`. L'assegnazione dell'insegnante all'allievo è in `StudentSerializer.create`. La validazione pagamento-pacchetto è duplicata tra `Payment.clean` e `PaymentSerializer.validate`.

**Intervento.** Service layer esplicito: `services.py` per le scritture e `selectors.py` per le letture complesse, in ogni app. View e serializer diventano sottili. **Correggere** (è uno spostamento di codice, non una riscrittura). ADR-002.

### G4. Bug: creazione di un pacchetto impossibile senza `lessons_remaining`. Gravità: media

`PackageSerializer.create` imposta `lessons_remaining = total_lessons` se manca. Ma il campo è obbligatorio nel serializer, quindi la validazione fallisce prima di arrivare a `create`. Verificato: POST senza `lessons_remaining` restituisce 400. Inoltre `lessons_remaining` è scrivibile via PATCH, quindi il contatore può essere modificato a mano senza passare dalla logica di dominio.

**Intervento.** Campo in sola lettura, valorizzato dal service alla creazione. **Correggere.**

### G5. Input non validato produce errore 500. Gravità: media

`GET /api/v1/lessons/?week=garbage` solleva `ValueError` e restituisce 500. Verificato. **Intervento:** validare il parametro e restituire 400.

### G6. Nessuna CI, nessun type checking, nessun pre-commit. Gravità: alta

Non esiste `.github/workflows/`. mypy non è installato. **Intervento:** GitHub Actions con ruff, mypy (django-stubs e djangorestframework-stubs) e pytest su PostgreSQL e Redis veri. Pre-commit con gli stessi controlli. La regola "blocca il merge" richiede anche la branch protection su GitHub: va attivata da te (vedi `docs/learning/concetti/ci-e-quality-gate.md`).

### G7. Riferimenti AWS. Gravità: media (requisito esplicito)

`infra/aws/README.md`, la constitution (sezione Stack), `README.md`, `specs/001-musicstudio-mvp/plan.md`, `research.md` e `tasks.md` parlano di ECS, RDS, ElastiCache, ECR, Route 53. Non ci sono dipendenze Python AWS (niente boto3). **Intervento:** cancellare `infra/aws/` e sostituire i riferimenti con Coolify. Nei documenti storici della feature 001 aggiungo una nota invece di riscriverli, per non falsare la storia. ADR-003.

### G8. Docker non pronto per la produzione. Gravità: alta

- Porte pubblicate sull'host per tutti i servizi, compresi database e Redis.
- Healthcheck solo sul database. Niente su redis, backend, worker, beat.
- Il backend in Compose usa `runserver`, il server di sviluppo.
- Immagine eseguita come root. `uv:latest` non fissato, quindi build non riproducibili.
- Nessun file Compose per la produzione. Nessun backup del database.
- I file statici dell'admin non vengono serviti in produzione (manca whitenoise o un web server).

**Intervento:** Dockerfile multi-stage con utente non root e healthcheck. Due file Compose: `docker-compose.yml` per lo sviluppo e `docker-compose.coolify.yml` per la produzione (nessuna porta pubblicata, healthcheck su ogni servizio, variabili obbligatorie con `${VAR:?}`, servizio di backup schedulato). ADR-003 e ADR-005.

### G9. Configurazione per ambienti incompleta. Gravità: media

- Manca un settings per i test. I test usano `dev`, che ha `ALLOWED_HOSTS = ["*"]`.
- `prod.py` non gestisce il proxy TLS (`SECURE_PROXY_SSL_HEADER`). Dietro il proxy di Coolify questo causa un loop di redirect HTTPS.
- Mancano `CSRF_TRUSTED_ORIGINS` (necessario per l'admin dietro HTTPS), il logging e la cache.
- `CELERY_RESULT_BACKEND` legge la variabile del broker. Funziona, ma è confuso.
- Il path dell'admin è fisso su `/admin/`.

**Intervento:** settings `base`, `dev`, `test`, `prod`, tutto guidato da variabili d'ambiente e documentato in `.env.example`. ADR-004.

### G10. Nessun health endpoint. Gravità: media

Coolify e Docker hanno bisogno di sapere se il container è vivo e pronto. **Intervento:** `/health/live/` (il processo risponde, nessuna dipendenza) e `/health/ready/` (database e Redis raggiungibili). ADR-006.

### G11. Nessun rate limiting. Gravità: media

L'endpoint `auth/token/` accetta tentativi di login illimitati (OWASP API4, consumo di risorse senza limiti, e brute force). **Intervento:** throttling di DRF, con limiti più stretti sul login e la cache su Redis.

### G12. Django 5.1 fuori supporto. Gravità: media

Django 5.1 non riceve più patch di sicurezza da dicembre 2025. **Intervento:** passare a Django 5.2 LTS (supportata fino ad aprile 2028).

### G13. Task dei promemoria non sicuro in concorrenza. Gravità: media

`send_lesson_reminders` legge le lezioni, invia le email e poi marca `reminder_sent_at`. Se due esecuzioni si sovrappongono, o se il worker si ferma a metà, lo stesso genitore può ricevere due email. Inoltre il task importa l'app Celery da `config.celery` invece di usare `shared_task`. **Intervento minimo nella fase 1:** "reclamare" la lezione con un `UPDATE ... WHERE reminder_sent_at IS NULL` prima di inviare (semantica at-most-once), più prefetch dei genitori. L'idempotenza completa dei task è un argomento della fase 3.

### G14. Indici mancanti. Gravità: bassa (oggi), media (con i dati)

Le query più frequenti filtrano `Lesson` per insegnante e data, `Lesson` per stato e data (promemoria), `Payment` per allievo e data e `Package` per allievo e data di acquisto. Esistono solo gli indici automatici sulle foreign key. **Intervento:** indici composti dichiarati in `Meta.indexes`, verificati con `EXPLAIN`.

### G15. Studio owner senza profilo Teacher produce errore 500. Gravità: bassa

`MyStudioView.get_object` accede a `request.user.teacher.studio`. Se l'utente ha ruolo `studio_owner` ma non ha un profilo, l'endpoint va in errore. **Intervento:** 404 esplicito.

### G16. Password demo fissa in `seed_demo`. Gravità: bassa

`password123` per tutti gli utenti demo. È accettabile solo in sviluppo. **Intervento:** il comando si rifiuta di girare con `DEBUG=False`, a meno di un flag esplicito.

### G17. Frontend. Gravità: nessuna (fuori scope)

`frontend/` è una SPA React + Vite. Per le regole di questa fase non viene toccato né cancellato. È già isolato nella sua cartella. L'unico intervento è nel Compose di sviluppo: il servizio `frontend` diventa opzionale (Compose profile `frontend`), così il backend si avvia senza Node. Nota: l'app Expo del branch `app` parla con le API Next.js del branch `web`, non con queste. Allinearla è un lavoro futuro e non rientra in questa fase.

### G18. Segreti nella working directory (non nel repository). Gravità: alta, ma locale

Passando dal branch `app` sono rimasti file non tracciati: `.env.local` (credenziali reali di Neon e `AUTH_SECRET`) e `.expo/dev/logs/start.log` (che stampa le stesse variabili). Non sono mai stati committati, l'ho controllato su tutta la storia. Ho aggiunto entrambi a `.gitignore`. **Consiglio:** ruotare comunque la password di Neon e l'`AUTH_SECRET`, perché i log di Expo li contengono in chiaro.

## 5. Correggere o riscrivere?

Per tutti i gap la risposta è **correggere**. I motivi:

- I modelli e lo schema sono sensati. I vincoli nel database ci sono già.
- L'isolamento in lettura è già centralizzato in un punto solo. Va esteso, non ripensato.
- I 26 test esistenti diventano la rete di sicurezza del refactor: se restano verdi dopo lo spostamento della logica nei service, il comportamento non è cambiato.
- Una riscrittura costerebbe giorni e butterebbe via test e migrazioni che funzionano.

Non c'è quindi nessun ADR di riscrittura. L'unica scelta "grossa" è il punto di partenza (ADR-001), che non è una riscrittura ma un ripristino del codice Django già esistente.

## 6. Piano di intervento (fase 1)

1. Constitution aggiornata (spec-kit), poi spec, piano e task della feature `002-production-foundations`.
2. Upgrade a Django 5.2 LTS. mypy con gli stub. Configurazione di pytest con copertura.
3. Settings per ambienti e `.env.example`.
4. Service layer e selectors. Correzione di G1, G2, G3, G4, G5, G13, G15.
5. Indici con migrazione.
6. Health endpoint, throttling, whitenoise.
7. Docker multi-stage, Compose di sviluppo e Compose per Coolify con backup. Rimozione di AWS.
8. CI su GitHub Actions e pre-commit.
9. Test di regressione per ogni gap, `assertNumQueries` sugli endpoint principali.
10. Documentazione di studio.

## 7. Cosa resta fuori dalla fase 1

ExclusionConstraint contro le sovrapposizioni delle lezioni, multi-tenancy esplicita, OpenAPI rifinito (fase 2). Stripe, webhook, caching (fase 3). Sentry, log strutturati, Locust, checklist OWASP completa (fase 4). Sono nel piano della feature 002 come roadmap.

## 8. Aggiornamento: problemi emersi durante l'implementazione

Correggendo i gap sono venuti fuori altri difetti. Li elenco qui, perché fanno parte del quadro di partenza.

### G19. Modulo di settings di default vuoto. Gravità: alta

`config/wsgi.py`, `config/asgi.py` usavano `config.settings` come default, e `config/celery.py` usava `config.settings.dev`. Ma `config/settings/` è un package con `__init__.py` vuoto. Se la variabile `DJANGO_SETTINGS_MODULE` mancava, gunicorn partiva con impostazioni inesistenti. Funzionava solo perché il file `.env` la impostava. Celery in produzione sarebbe partito con le impostazioni di sviluppo. **Correzione:** i tre entrypoint di produzione usano `config.settings.prod`. `manage.py` resta su `dev`.

### G20. Il virtualenv nascosto dal bind mount. Gravità: alta

Il vecchio Compose montava `../backend` su `/app`. Il Dockerfile creava il virtualenv in `/app/.venv`. Il mount copriva la cartella dell'immagine, quindi il virtualenv spariva e il container non poteva partire. Non era mai stato verificato (il task T055 della feature 001 era rimasto aperto). **Correzione:** il virtualenv vive in `/opt/venv`.

### G21. Doppia scalatura del pacchetto in concorrenza. Gravità: media

`Lesson.mark_completed` controllava lo stato sull'oggetto in memoria. Due richieste quasi simultanee, ognuna con la propria copia della lezione, potevano scalare il pacchetto due volte. **Correzione:** `complete_lesson` blocca la riga della lezione con `select_for_update` e scala il pacchetto con un solo `UPDATE` condizionato. Un test riproduce il caso con una copia "vecchia" dell'oggetto.

### G22. Lezione collegata al pacchetto di un altro allievo. Gravità: media

Anche con lo scoping, un insegnante poteva collegare la lezione dell'allievo A al pacchetto dell'allievo B (entrambi suoi). Completando la lezione si scalava il pacchetto della famiglia sbagliata. **Correzione:** regola nel service `lessons.services`.

### G15 (esteso). Fuga di insegnanti tra tenant. Gravità: alta

Oltre all'errore 500, `StudioTeachersView` faceva `Teacher.objects.filter(studio=teacher.studio)`. Se il titolare non aveva uno studio, il filtro diventava `studio IS NULL` e restituiva **tutti gli insegnanti solisti di tutti i tenant**, con la loro email. **Correzione:** queryset vuoto. Test di regressione in `backend/apps/studios/tests/test_studio.py`.

### G23. `seed_demo` non idempotente. Gravità: bassa

Il comando dichiarava di poter essere rieseguito, ma creava una nuova lezione "tra 24 ore" a ogni esecuzione, perché la chiave di `get_or_create` era l'istante preciso. **Correzione:** chiave sulla data.

### Verifiche non eseguibili in questo ambiente

Docker non è disponibile nella WSL dove ho lavorato. Ho verificato le impostazioni di produzione avviando gunicorn senza Docker (liveness, readiness, redirect HTTPS, proxy TLS, file statici, host non ammessi), ma i due file Compose sono validati solo nella sintassi, non con un `docker compose up` reale. È il primo controllo da fare su una macchina con Docker (`specs/002-production-foundations/quickstart.md`, punti 4-6).
