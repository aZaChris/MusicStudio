# Panoramica dell'architettura di MusicStudio

## TL;DR

MusicStudio è un'API REST per insegnanti di musica e piccoli studi. Gestisce allievi, lezioni, pacchetti di lezioni prepagate, pagamenti e un portale in sola lettura per i genitori. È un monolite modulare Django: un solo deploy, un'app per ogni dominio, con la logica di business in service e selector. Gira in container Docker su Coolify, con PostgreSQL per i dati, Redis per code e cache, e Celery per i promemoria.

## Il prodotto in due minuti

Un insegnante privato di pianoforte ha venti allievi. Oggi usa un calendario, un foglio Excel per i pagamenti e WhatsApp per i genitori. MusicStudio mette tutto in un posto.

Gli attori sono tre.

- **L'insegnante** vede la sua settimana, segna le lezioni come fatte, registra i pagamenti.
- **Il titolare dello studio** fa le stesse cose, ma per tutti gli insegnanti del suo studio.
- **Il genitore** vede, in sola lettura, le lezioni, i pacchetti e i pagamenti dei suoi figli. Riceve un'email il giorno prima di ogni lezione.

Il concetto di business più importante è il **pacchetto**. Un genitore compra, per esempio, otto lezioni. Ogni lezione completata ne scala una. Quando ne restano due, l'insegnante vede un avviso. Questo contatore deve essere sempre giusto: se sbaglia, qualcuno perde soldi.

## Il sistema dall'alto

Immagina cinque scatole.

1. **Il proxy di Coolify** riceve il traffico HTTPS da Internet, gestisce il certificato e inoltra le richieste al backend.
2. **Il backend web**: Django con Django REST Framework, servito da gunicorn. Espone l'API su `/api/v1/`, la documentazione OpenAPI su `/api/docs/` e i controlli di salute su `/health/`.
3. **PostgreSQL**: tutti i dati.
4. **Redis**: la coda dei task di Celery e la cache usata per il rate limiting.
5. **Celery**: un worker che esegue i task e un processo beat che li programma. Oggi c'è un solo task: ogni 15 minuti, i promemoria delle lezioni di domani.

In più c'è un sesto servizio di supporto, il **backup**, che ogni notte salva il database.

Backend, worker e beat usano la stessa immagine Docker. Cambia solo il comando di avvio.

## Dentro il backend

Il codice è in `backend/`. La configurazione Django è in `backend/config/`, le app di dominio in `backend/apps/`:

- `accounts`: l'utente, con il login tramite email e il ruolo.
- `studios`: studi e insegnanti.
- `students`: allievi e collegamenti con i genitori.
- `packages`: i pacchetti di lezioni.
- `lessons`: le lezioni e la dashboard dell'insegnante.
- `payments`: i pagamenti, registrati a mano (contanti, bonifico).
- `notifications`: i promemoria via email.
- `common`: codice trasversale. Lo scoping per tenant, i permessi, l'exception handler, le factory dei test.

Dentro ogni app la struttura è sempre la stessa. `models.py` per i dati e i vincoli. `services.py` per le operazioni di scrittura. `selectors.py` per le letture. `serializers.py` e `views.py` per l'HTTP, il più sottili possibile. `tests/` per i test.

Una richiesta tipica, per esempio "crea una lezione", passa così: la view riceve il JSON, il serializer lo valida (compreso il controllo che l'allievo sia visibile all'utente), la view chiama `services.create_lesson`, il service applica le regole e salva, il serializer restituisce il risultato.

## Le scelte e il loro perché

**Django e DRF.** Django dà ORM, migrazioni, admin e autenticazione già pronti. DRF aggiunge serializer, viewset, permessi, paginazione e throttling. Per un'API con dati relazionali e regole di accesso per ruolo è la scelta più produttiva in Python. L'alternativa più seria era FastAPI: più moderno e veloce, ma senza admin, migrazioni e ORM integrati, che qui servono tutti.

**PostgreSQL.** I dati sono relazionali: allievi, lezioni, pacchetti e pagamenti sono collegati tra loro. Servono transazioni, vincoli e lock di riga. Nella fase 2 useremo anche un vincolo di esclusione per impedire lezioni sovrapposte, che esiste solo in PostgreSQL.

**Celery e Redis.** Il promemoria non deve bloccare una richiesta HTTP e deve partire anche se nessuno usa l'app. Serve un processo in background con una schedulazione. Celery è lo standard in Django. Redis fa da coda ed è già usato per la cache.

**Monolite modulare.** Un solo deploy è semplice da gestire. I moduli per dominio tengono il codice ordinato. Per uno studio da dieci insegnanti, i microservizi aggiungerebbero solo costi. Dettagli in `docs/learning/adr/ADR-002-modular-monolith-e-service-layer.md`.

**JWT.** L'API ha più client: una SPA web e, in futuro, un'app mobile. Un token nell'intestazione funziona allo stesso modo per entrambi, senza cookie e senza CSRF.

**Coolify invece di AWS.** Le linee guida escludono AWS. Coolify dà dominio, HTTPS e deploy da Git su un server qualsiasi, con un costo fisso e basso. Dettagli in `docs/learning/adr/ADR-003-coolify-al-posto-di-aws.md`.

**uv.** Gestore di pacchetti Python molto veloce, con un lockfile che rende identiche le installazioni in locale, in CI e nell'immagine Docker.

**pytest, ruff, mypy.** pytest per test leggibili. ruff per lint e formattazione in un solo strumento veloce. mypy con gli stub di Django e DRF per trovare errori di tipo prima dell'esecuzione.

## Come è protetto

La regola più importante del progetto è l'isolamento tra tenant: un utente non deve mai leggere o scrivere i dati di un altro insegnante o di un'altra famiglia. È applicata nel database, tramite i queryset, sia in lettura sia in scrittura, da un unico modulo: `backend/apps/common/scoping.py`. Ogni endpoint di scrittura ha un test che prova a violarla. Il resto della sicurezza (rate limiting, configurazione di produzione, OWASP) è in `docs/learning/concetti/sicurezza-api-owasp.md`.

## Come si verifica la qualità

A ogni push GitHub Actions esegue lint, formattazione, tipi, controllo delle migrazioni, 92 test con copertura minima del 90% su PostgreSQL e Redis veri, e la generazione dello schema OpenAPI. In locale gli stessi controlli veloci girano prima di ogni commit.

## Cosa è discutibile, detto onestamente

- **Un solo server.** Se cade, cade tutto, backup compresi. È accettabile per la scala del prodotto, ma è un limite reale.
- **Migrazioni all'avvio del web.** Semplici e sicure con una replica, non con più repliche.
- **Lo scoping per ruolo ha tre rami.** Funziona, ma con altri ruoli diventerebbe fragile. La fase 2 introduce un tenant esplicito.
- **Il frontend esistente** (`frontend/`, una SPA React) e l'app Expo del branch `app` parlano con API diverse: la SPA con queste, l'app con quelle Next.js del branch `web`. Riallinearli è un lavoro futuro.
- **Docker non è stato eseguito** nell'ambiente in cui è stata scritta la fase 1. Le impostazioni di produzione sono state provate con gunicorn, ma il primo `docker compose up` reale è ancora da fare.

## Dove andare dopo

- Per capire da dove siamo partiti: `docs/learning/audit-iniziale.md`.
- Per le decisioni: la cartella `docs/learning/adr/`.
- Per i concetti, uno per file: la cartella `docs/learning/concetti/`.
- Per prepararti al colloquio: `docs/learning/colloquio/domande-e-risposte.md`.
