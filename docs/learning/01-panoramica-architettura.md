# Panoramica dell'architettura di MusicStudio

## TL;DR

MusicStudio è un'API REST per insegnanti di musica e piccoli studi. Gestisce allievi, lezioni, pacchetti di lezioni prepagate, pagamenti e un portale in sola lettura per i genitori. È un monolite modulare Django: un solo deploy, un'app per ogni dominio, con la logica di business in service e selector. Gira in container Docker su Coolify, con PostgreSQL per i dati, Redis per code e cache, e Celery per i promemoria.

## Il prodotto in due minuti

Un insegnante privato di pianoforte ha venti allievi. Oggi usa un calendario, un foglio Excel per i pagamenti e WhatsApp per i genitori. MusicStudio mette tutto in un posto.

Gli attori sono tre.

- **L'insegnante** vede la sua settimana, segna le lezioni come fatte, registra i pagamenti.
- **Il titolare dello studio** fa le stesse cose, ma per tutti gli insegnanti del suo studio.
- **Il genitore** vede, in sola lettura, le lezioni, i pacchetti e i pagamenti dei suoi figli. Riceve un'email il giorno prima di ogni lezione.

Un'altra regola è garantita direttamente dal database: un insegnante non può avere due lezioni sovrapposte, e un allievo nemmeno. Lo impediscono due vincoli di esclusione di PostgreSQL, che funzionano anche con richieste simultanee.

Il concetto di business più importante è il **pacchetto**. Un genitore compra, per esempio, otto lezioni. Ogni lezione completata ne scala una. Quando ne restano due, l'insegnante vede un avviso. Questo contatore deve essere sempre giusto: se sbaglia, qualcuno perde soldi.

## Il sistema dall'alto

Immagina cinque scatole.

1. **Il proxy di Coolify** riceve il traffico HTTPS da Internet, gestisce il certificato e inoltra le richieste al backend o al portale web, ognuno con il suo dominio.
2. **Il backend web**: Django con Django REST Framework, servito da gunicorn. Espone l'API su `/api/v1/`, la documentazione OpenAPI su `/api/docs/` e i controlli di salute su `/health/`.
3. **PostgreSQL**: tutti i dati.
4. **Redis**: la coda dei task di Celery e la cache (rate limiting e dashboard).
5. **Celery**: un worker che esegue i task e un processo beat che li programma. Ogni 15 minuti registra e invia i promemoria delle lezioni di domani; elabora i webhook di Stripe; ogni ora riconcilia con Stripe i pagamenti rimasti aperti.

In più ci sono due servizi di supporto. Il **backup** ogni notte salva il database in un volume. L'**offsite** copia quei dump, cifrati, su un bucket fuori dal server, così sopravvivono anche alla perdita della macchina. E c'è un servizio esterno: **Stripe**, che gestisce i pagamenti online in modalità test, con una pagina di pagamento ospitata e notifiche via webhook.

Backend, worker e beat usano la stessa immagine Docker. Cambia solo il comando di avvio.

C'è poi il **portale web** (`frontend/`): una SPA React servita da nginx senza privilegi, che parla con le API dal browser. I suoi tipi sono generati dal contratto OpenAPI, la sessione segue la rotazione dei refresh token, e il suo container manda una Content-Security-Policy stretta (ADR-023…025). Un'app mobile, con lo stesso contratto, vive sul branch `refactor/mobile`.

## Dentro il backend

Il codice è in `backend/`. La configurazione Django è in `backend/config/`, le app di dominio in `backend/apps/`:

- `accounts`: l'utente, con il login tramite email e il ruolo.
- `studios`: studi e insegnanti.
- `students`: allievi e collegamenti con i genitori.
- `packages`: i pacchetti di lezioni.
- `lessons`: le lezioni e la dashboard dell'insegnante.
- `payments`: i pagamenti, registrati a mano (contanti, bonifico) o online con Stripe Checkout, i webhook e la riconciliazione.
- `notifications`: i promemoria via email, con una outbox che li rende affidabili.
- `common`: codice trasversale. Lo scoping per tenant, i permessi, l'exception handler, le factory dei test.

Dentro ogni app la struttura è sempre la stessa. `models.py` per i dati e i vincoli. `services.py` per le operazioni di scrittura. `selectors.py` per le letture. `serializers.py` e `views.py` per l'HTTP, il più sottili possibile. `tests/` per i test.

Una richiesta tipica, per esempio "crea una lezione", passa così: la view riceve il JSON, il serializer lo valida (compreso il controllo che l'allievo sia visibile all'utente), la view chiama `services.create_lesson`, il service applica le regole e salva, il serializer restituisce il risultato.

## Le scelte e il loro perché

**Django e DRF.** Django dà ORM, migrazioni, admin e autenticazione già pronti. DRF aggiunge serializer, viewset, permessi, paginazione e throttling. Per un'API con dati relazionali e regole di accesso per ruolo è la scelta più produttiva in Python. L'alternativa più seria era FastAPI: più moderno e veloce, ma senza admin, migrazioni e ORM integrati, che qui servono tutti.

**PostgreSQL.** I dati sono relazionali: allievi, lezioni, pacchetti e pagamenti sono collegati tra loro. Servono transazioni, vincoli e lock di riga. Nella fase 2 useremo anche un vincolo di esclusione per impedire lezioni sovrapposte, che esiste solo in PostgreSQL.

**Celery e Redis.** Il promemoria non deve bloccare una richiesta HTTP e deve partire anche se nessuno usa l'app. Serve un processo in background con una schedulazione. Celery è lo standard in Django. Redis fa da coda ed è già usato per la cache.

**Monolite modulare.** Un solo deploy è semplice da gestire. I moduli per dominio tengono il codice ordinato. Per uno studio da dieci insegnanti, i microservizi aggiungerebbero solo costi. Dettagli in `docs/learning/adr/ADR-002-modular-monolith-e-service-layer.md`.

**JWT.** L'API ha più client: una SPA web e, in futuro, un'app mobile. Un token nell'intestazione funziona allo stesso modo per entrambi, senza cookie e senza CSRF. Dalla fase 4 i refresh token sono revocabili con una lista nera, e il token di accesso dura 15 minuti (ADR-018).

**Coolify invece di AWS.** Le linee guida escludono AWS. Coolify dà dominio, HTTPS e deploy da Git su un server qualsiasi, con un costo fisso e basso. Dettagli in `docs/learning/adr/ADR-003-coolify-al-posto-di-aws.md`.

**uv.** Gestore di pacchetti Python molto veloce, con un lockfile che rende identiche le installazioni in locale, in CI e nell'immagine Docker.

**pytest, ruff, mypy.** pytest per test leggibili. ruff per lint e formattazione in un solo strumento veloce. mypy con gli stub di Django e DRF per trovare errori di tipo prima dell'esecuzione.

## Come è protetto

La regola più importante del progetto è l'isolamento tra tenant: un utente non deve mai leggere o scrivere i dati di un altro studio o di un'altra famiglia. Il tenant è lo **studio**: ogni insegnante e ogni allievo ne ha uno, e un insegnante solista ha uno studio personale. A ogni richiesta un contesto (ruolo, studio, profilo) viene calcolato una volta, e tutti i queryset passano da un unico modulo: `backend/apps/common/scoping.py`. Sopra la visibilità, un permesso per oggetto decide chi può modificare cosa. Ogni endpoint di scrittura ha un test che prova a violarla. Dalla fase 7 ci sono account veri: registrazione con conferma email, reset della password, inviti per insegnanti, genitori e studenti adulti, blocco dopo password sbagliate e verifica in due passaggi per titolari e insegnanti. Le note delle lezioni sono cifrate nel database, ogni azione delicata finisce in un registro che il titolare può leggere, e una famiglia può scaricare i suoi dati o cancellarli. Il resto della sicurezza (rate limiting, configurazione di produzione, OWASP) è in `docs/learning/concetti/sicurezza-api-owasp.md`.

## Come si osserva in produzione

Ogni richiesta ha un request id, che torna al client nell'header `X-Request-ID` e finisce in ogni riga di log, anche dei task Celery che la richiesta avvia. In produzione i log sono JSON, una riga per evento, con una riga di accesso per richiesta. Gli errori vanno a Sentry, se configurato, ripuliti da token, cookie ed email. Il runbook in `docs/operations/runbook.md` spiega deploy, rollback, rotazione dei segreti e ripristino.

## Come si verifica la qualità

A ogni push GitHub Actions esegue lint, formattazione, tipi, controllo delle migrazioni, i test con copertura minima del 90% su PostgreSQL e Redis veri, e il confronto tra lo schema OpenAPI generato e quello salvato nel repository (`backend/openapi.yaml`), che è il contratto con i client. Dalla fase 4 gira anche `manage.py check --deploy` con i settings di produzione. Un load test con Locust (`backend/loadtest/`) misura quanto regge l'API, con i risultati in `docs/loadtest/`. In locale gli stessi controlli veloci girano prima di ogni commit.

## Cosa è discutibile, detto onestamente

- **Un solo server.** Se cade, l'app è ferma finché non si ripristina altrove. I backup ora sono anche fuori dal server, ma il ripristino dal bucket vero è ancora da provare.
- **Migrazioni all'avvio del web.** Semplici e sicure con una replica, non con più repliche.
- **La coerenza dello studio** tra un allievo e il suo insegnante è garantita dai service, non da un vincolo del database.
- **Il refresh token del portale web sta in `localStorage`**: uno script iniettato potrebbe leggerlo. È un rischio accettato e documentato (ADR-023); il passo successivo è un cookie httpOnly.
- **Docker non è stato eseguito** nell'ambiente di sviluppo. Le impostazioni di produzione sono state provate con gunicorn, anche sotto carico; l'immagine del portale la costruisce e la prova la CI. Il primo deploy reale su Coolify è ancora da fare.
- **I testi legali sono bozze.** Il registro dei trattamenti e le informative (`docs/privacy/`) vanno validati da un professionista prima di usare l'app con famiglie vere, e i tempi di conservazione sono una proposta.
- **Il blocco dell'account si può usare contro una persona**: chi conosce un'email può bloccarla. Il tetto di 24 ore e il reset via email lo limitano.
- **I numeri del load test** vengono da un portatile, con client e server sulla stessa CPU. Servono a trovare problemi, non a promettere prestazioni.

## Dove andare dopo

- Per capire da dove siamo partiti: `docs/learning/audit-iniziale.md`.
- Per le decisioni: la cartella `docs/learning/adr/`.
- Per i concetti, uno per file: la cartella `docs/learning/concetti/`.
- Per prepararti al colloquio: `docs/learning/colloquio/domande-e-risposte.md`.
- Per mettere in produzione e gestire l'app: `docs/operations/runbook.md`.
