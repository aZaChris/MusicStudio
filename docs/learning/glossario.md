# Glossario

Ogni termine è in inglese, come lo troverai nel codice e nei colloqui, con una spiegazione in italiano semplice. In ordine alfabetico.

**ADR (Architecture Decision Record).** Un breve documento che registra una decisione tecnica: il contesto, la scelta, le alternative scartate e le conseguenze. Serve a ricordare perché si è fatta una scelta.

**Annotation (annotazione).** In Django, un valore calcolato dal database e aggiunto a ogni riga del risultato, per esempio con `annotate(...)`. Evita di calcolarlo in Python riga per riga.

**API (Application Programming Interface).** L'insieme di indirizzi e regole con cui un programma ne usa un altro. Qui: gli endpoint HTTP sotto `/api/v1/`.

**At-most-once / at-least-once.** Garanzie di consegna. At-most-once: un messaggio arriva una volta o mai, senza duplicati ma con possibili perdite. At-least-once: arriva almeno una volta, senza perdite ma con possibili duplicati.

**Backup rotation (rotazione dei backup).** La regola su quante copie tenere. Noi teniamo 7 giornaliere, 4 settimanali e 6 mensili.

**Bind mount.** Una cartella del computer montata dentro un container. In sviluppo serve a vedere subito le modifiche al codice.

**BOLA (Broken Object Level Authorization).** Una falla in cui il server non controlla che l'oggetto richiesto appartenga all'utente. È il primo rischio della OWASP API Top 10.

**Branch protection.** Una regola di GitHub che impedisce il merge su un branch se mancano revisioni o se la CI è rossa.

**B-tree index.** Il tipo di indice più comune in PostgreSQL: una struttura ordinata che trova valori e intervalli in pochi passi.

**Canonical (link canonico).** Un tag che dice a Google qual è l'indirizzo ufficiale di una pagina, quando si può raggiungere da più strade.

**Celery.** Una libreria Python per eseguire task in background, fuori dalle richieste HTTP.

**Celery Beat.** Il processo di Celery che lancia i task a orari prestabiliti, come un cron.

**CI (Continuous Integration).** Un sistema che a ogni push controlla automaticamente il codice: lint, test, build.

**Claim (reclamare).** Segnare un lavoro come "preso" in modo atomico, così che un altro processo non lo faccia di nuovo. Noi lo facciamo con un `UPDATE ... WHERE stato = 'in attesa'` sulle consegne dei promemoria.

**Composite index (indice composto).** Un indice su più colonne, per esempio insegnante e data insieme.

**Container.** Un processo isolato che gira con tutto ciò che gli serve, creato da un'immagine Docker.

**Coolify.** Una piattaforma self-hosted che fa il deploy di applicazioni da Git, con dominio e HTTPS. Simile a Heroku, ma sul tuo server.

**Coverage (copertura).** La percentuale di codice eseguita dai test. Non misura la qualità dei test, ma segnala il codice mai provato.

**CSRF (Cross-Site Request Forgery).** Un attacco in cui un sito esterno fa compiere al browser dell'utente un'azione non voluta. Django lo blocca con un token.

**DRF (Django REST Framework).** La libreria che aggiunge a Django serializer, viewset, permessi e throttling per costruire API.

**Endpoint.** Un indirizzo dell'API con un metodo HTTP, per esempio `POST /api/v1/lessons/`.

**Entrypoint.** Lo script che un container esegue all'avvio. Il nostro sceglie se diventare web, worker o beat.

**Exception handler.** La funzione che trasforma un'eccezione in una risposta HTTP. Il nostro converte gli errori di validazione di Django in un 400.

**EXPLAIN ANALYZE.** Il comando PostgreSQL che esegue una query e mostra come l'ha eseguita: indici usati, righe lette, tempi.

**Factory (factory_boy).** Una classe che crea oggetti di test con valori sensati, così nel test scrivi solo il dato che conta.

**Fail fast.** Il principio di fermarsi subito, con un errore chiaro, appena qualcosa non va. Per esempio, non avviare l'app se manca un segreto.

**Fixture.** In pytest, una risorsa preparata per i test, come un database pulito o un client.

**Gunicorn.** Un server HTTP per applicazioni Python in produzione. Gestisce più processi in parallelo.

**Healthcheck.** Un controllo automatico che dice se un servizio funziona.

**HSTS (HTTP Strict Transport Security).** Un'intestazione che dice al browser di usare sempre HTTPS per quel dominio.

**Idempotent (idempotente).** Un'operazione che produce lo stesso risultato se eseguita una o più volte. Completare due volte la stessa lezione scala il pacchetto una volta sola.

**Index (indice).** Una struttura del database che velocizza la ricerca delle righe, al costo di spazio e scritture più lente.

**JWT (JSON Web Token).** Un token firmato che il client manda a ogni richiesta per dimostrare chi è.

**Lighthouse.** Uno strumento di Google, dentro il browser, che controlla una pagina e dà voti su prestazioni, accessibilità e SEO.

**Liveness probe.** Il controllo "il processo è vivo?". Se fallisce, il container va riavviato.

**Lockfile.** Il file che fissa le versioni esatte di tutte le dipendenze (`uv.lock`), per installazioni identiche ovunque.

**Migration (migrazione).** Un file che descrive una modifica allo schema del database, applicata con `migrate`.

**Modular monolith (monolite modulare).** Un'unica applicazione deployabile, divisa all'interno in moduli per dominio con confini chiari.

**Multi-stage build.** Un Dockerfile con più fasi: una per costruire, una finale più piccola con solo il necessario.

**Multi-tenancy.** Un solo sistema che serve più clienti separati (tenant), ognuno con i propri dati isolati.

**mypy.** Lo strumento che controlla i tipi in Python senza eseguire il codice.

**N+1 query problem.** Una query per la lista, più una query per ogni elemento. Fa crescere il lavoro del database con i dati.

**noindex (X-Robots-Tag).** Un'intestazione HTTP che dice ai motori di ricerca di non mostrare quella pagina nei risultati. In MusicStudio è il valore predefinito del sito, e l'API lo manda sempre.

**Open Graph.** Tag nella pagina che decidono titolo, descrizione e immagine dell'anteprima quando si condivide un link su un social o in una chat.

**OpenAPI.** Un formato standard per descrivere un'API. Da qui si genera la documentazione interattiva.

**ORM (Object-Relational Mapper).** Lo strato che traduce oggetti Python in query SQL e viceversa.

**OWASP.** Un'organizzazione no-profit che pubblica guide e liste dei rischi di sicurezza, come la API Security Top 10.

**Partial index (indice parziale).** Un indice che contiene solo le righe che rispettano una condizione.

**pre-commit.** Uno strumento che esegue controlli automatici prima di ogni commit.

**Prefetch (`prefetch_related`).** Carica in una query separata gli oggetti collegati di tutta una lista, invece che uno per volta.

**Queryset.** In Django, una query non ancora eseguita, che si può filtrare e combinare.

**Rate limiting / throttling.** Limitare quante richieste un client può fare in un intervallo di tempo.

**Readiness probe.** Il controllo "il servizio può ricevere traffico?". Controlla le dipendenze, come database e Redis.

**Redis.** Un database in memoria, molto veloce. Qui fa da coda per Celery e da cache.

**Reverse proxy.** Il server che sta davanti all'applicazione, riceve le richieste da Internet e le inoltra. In Coolify gestisce anche HTTPS.

**robots.txt.** Un file a un indirizzo fisso che dice ai crawler dove possono entrare. Non decide l'indicizzazione: per quella servono `noindex` o i tag nella pagina.

**RPO / RTO.** Recovery Point Objective: quanti dati puoi perdere. Recovery Time Objective: quanto tempo serve per ripartire.

**ruff.** Uno strumento molto veloce per lint e formattazione del codice Python.

**Scoping.** Restringere un queryset ai soli dati che un utente può vedere.

**`select_for_update`.** Blocca le righe lette fino alla fine della transazione, così nessun altro le modifica nel frattempo.

**`select_related`.** Carica gli oggetti collegati "verso uno" nella stessa query, con una JOIN.

**Selector.** Nel nostro codice, una funzione di lettura che restituisce un queryset già filtrato e ottimizzato.

**Serializer.** In DRF, la classe che valida i dati in ingresso e trasforma gli oggetti in JSON.

**Service layer.** Lo strato di funzioni che contiene le operazioni di business di scrittura.

**Sidecar.** Un container di supporto accanto a quello principale, come il nostro servizio di backup.

**Sitemap.** Un file XML con l'elenco degli indirizzi di un sito da proporre ai motori di ricerca. In MusicStudio contiene solo le pagine pubbliche.

**Spec-kit.** Il flusso di lavoro che usiamo: constitution, specifica, piano, task, implementazione.

**Subquery.** Una query dentro un'altra. Con `OuterRef` può riferirsi alla riga della query esterna.

**Tenant.** Un cliente isolato del sistema: un insegnante solista, uno studio, una famiglia.

**Throttle scope.** In DRF, un nome che lega una view a un limite specifico, come `login`.

**TLS termination.** Il punto in cui la connessione HTTPS viene decifrata. Da noi è il proxy di Coolify.

**Twelve-Factor App.** Una metodologia per applicazioni web. Tra le regole: configurazione nelle variabili d'ambiente.

**uv.** Un gestore di pacchetti e ambienti Python molto veloce, con lockfile.

**Volume.** Uno spazio di archiviazione gestito da Docker che sopravvive alla ricreazione dei container.

**Whitenoise.** Una libreria che permette a Django di servire i file statici in produzione, senza un web server separato.

**Worker.** Il processo Celery che esegue i task presi dalla coda.

## Termini aggiunti nella fase 2

**btree_gist.** Un'estensione di PostgreSQL che permette di usare confronti normali, come `=` su un id, dentro un indice GiST insieme agli intervalli.

**Contract-first / code-first.** Due modi di mantenere un contratto API. Contract-first: prima lo schema, poi il codice. Code-first: lo schema è generato dal codice.

**Deadlock.** Due transazioni che si aspettano a vicenda. PostgreSQL lo rileva e interrompe una delle due con il codice 40P01.

**Defense in depth (difesa in profondità).** Più livelli di protezione indipendenti, così se uno fallisce gli altri reggono.

**ExclusionConstraint.** Un vincolo di PostgreSQL che vieta a due righe di soddisfare insieme una serie di confronti, per esempio "stesso insegnante e orari sovrapposti".

**GiST index.** Un tipo di indice di PostgreSQL adatto a forme, intervalli e ricerche di sovrapposizione.

**Half-open interval (intervallo semiaperto).** Un intervallo che include l'inizio ed esclude la fine, scritto `[)`. Due lezioni consecutive non si sovrappongono.

**IMMUTABLE / STABLE.** Categorie delle funzioni di PostgreSQL. Una funzione immutabile dà sempre lo stesso risultato con gli stessi argomenti. Una stabile può dipendere da impostazioni come il fuso orario. Negli indici sono ammesse solo le immutabili.

**Object-level permission (permesso per oggetto).** In DRF, il controllo `has_object_permission`: decide se l'utente può agire su quell'oggetto preciso.

**Postprocessing hook.** In drf-spectacular, una funzione che modifica lo schema OpenAPI dopo la generazione.

**Race condition.** Un errore che dipende da chi arriva prima tra due operazioni quasi simultanee.

**Range type.** Un tipo di PostgreSQL che rappresenta un intervallo, per esempio `tstzrange` per intervalli di date e ore con fuso.

**Row Level Security (RLS).** Una funzione di PostgreSQL che filtra le righe in base all'utente o al tenant della sessione, direttamente nel database.

**Savepoint.** Un punto dentro una transazione a cui si può tornare in caso di errore, senza annullare tutta la transazione. In Django: un `atomic()` dentro un altro.

**State machine (macchina a stati).** Un insieme di stati e di passaggi ammessi tra loro. Il pagamento: in attesa, pagato, scaduto, con "pagato" finale.

**Tag (OpenAPI).** Un'etichetta che raggruppa le operazioni nella documentazione, per noi una per dominio.

**TenantContext.** Nel nostro codice, l'oggetto immutabile con ruolo, studio e profilo dell'utente, calcolato una volta per richiesta.

**Wall-clock time (ora da orologio).** L'ora come la legge una persona nel suo fuso. Sommare minuti in ora da orologio sbaglia nei cambi d'ora; per le durate si usa UTC.

## Termini aggiunti nella fase 3

**Acks late.** Impostazione di Celery: il messaggio di un task si conferma solo quando il task finisce, così un task interrotto torna in coda.

**At-least-once (almeno una volta).** Garanzia di consegna senza perdite, ma con possibili duplicati, che vanno riconosciuti.

**Backoff esponenziale.** Strategia di retry con attese che raddoppiano: 30 secondi, 60, 120, e così via.

**Cache-aside.** Il codice guarda prima in cache; se non trova, calcola, salva e restituisce.

**Checkout Session.** In Stripe, una sessione di pagamento con una pagina ospitata da Stripe.

**Dynamic payment methods.** Stripe sceglie i metodi di pagamento più adatti al cliente, configurati dalla Dashboard, invece di una lista fissa nel codice.

**Fail open.** Quando un controllo non può funzionare (per esempio la cache del rate limiting è giù), lascia passare invece di bloccare.

**HMAC.** Una firma calcolata con un segreto condiviso. Stripe la usa per firmare i webhook.

**Idempotency key.** Una chiave inviata con una richiesta: se arriva due volte, il servizio esegue solo la prima.

**Lease.** Un "prestito" a tempo: un worker tiene un lavoro per un tempo massimo, poi un altro può riprenderlo.

**Outbox (transactional outbox).** Una tabella in cui si registra cosa va inviato, nella stessa transazione dei dati; un processo separato la legge e invia.

**PCI DSS.** Le regole di sicurezza per chi gestisce dati delle carte di pagamento.

**Reconciliation (riconciliazione).** Confrontare il nostro stato con quello di un sistema esterno per trovare e correggere differenze.

**Restricted API key (chiave ristretta).** Chiave Stripe (`rk_`) con solo i permessi assegnati.

**Sandbox (Stripe).** Ambiente di prova isolato di Stripe, senza denaro reale.

**Signal (Django).** Un avviso che Django emette, per esempio dopo il salvataggio di un modello, a cui si può collegare una funzione.

**TTL (time to live).** Quanto a lungo una voce resta in cache.

**Visibility timeout.** In Redis come broker di Celery: dopo questo tempo un task non confermato viene riconsegnato.

**Webhook.** Una richiesta HTTP che un servizio esterno manda al nostro server quando succede qualcosa.

**Allowlist.** Un elenco di valori ammessi: tutto il resto è rifiutato. In MusicStudio il webhook di Stripe accetta solo gli indirizzi IP pubblicati da Stripe.

**ContextVar.** Una variabile Python che ha un valore diverso per ogni thread o coroutine. La usiamo per il request id, così due richieste contemporanee non si sovrascrivono.

**Dead man's switch.** Un allarme che scatta quando un segnale atteso **non** arriva. Il backup off-site chiama un URL a ogni copia riuscita: se un giorno la chiamata manca, arriva un'email.

**Load test (test di carico).** Un test che simula molti utenti insieme e misura tempi di risposta ed errori, per capire quanto regge il sistema e cosa cede per primo.

**Locust.** Uno strumento di load test in Python. Gli scenari sono classi Python con un metodo per ogni azione dell'utente.

**NUM_PROXIES.** L'impostazione di DRF che dice quanti proxy fidati ci sono davanti all'app. Senza, i throttle usano tutto `X-Forwarded-For` come identità del client, e il limite si aggira.

**Off-site backup.** Una copia dei backup in un luogo diverso dal server dei dati, così sopravvive se il server va perso.

**PBKDF2.** L'algoritmo con cui Django salva le password: ripete un hash un milione di volte, apposta lento, per rendere costoso indovinarle. Per questo il login consuma molta CPU.

**Percentile (p95, p99).** Il p95 è il tempo entro cui arriva il 95% delle risposte. Mostra quanto aspettano gli utenti più sfortunati, che la media nasconde.

**rclone crypt.** Un "remote" di rclone che cifra contenuto e nomi dei file prima di inviarli allo storage. Il provider vede solo dati cifrati.

**Refresh token rotation (rotazione).** A ogni rinnovo il client riceve un refresh token nuovo. Con la lista nera, quello vecchio diventa subito inutilizzabile.

**Request id.** Un identificativo assegnato a ogni richiesta e scritto in ogni riga di log, anche dei task che la richiesta avvia. Serve a ricostruire cosa è successo a una richiesta precisa.

**Restore drill (prova di ripristino).** Ripristinare davvero un backup in un database nuovo e controllare che i dati siano completi. Un backup mai ripristinato non è una garanzia.

**Sentry.** Un servizio che raccoglie gli errori di un'applicazione, raggruppa quelli uguali e manda avvisi.

**Structured logging (log strutturati).** Log in cui ogni riga è un oggetto con campi fissi, di solito JSON, invece di testo libero. Si possono filtrare per campo.

**Token blacklist (lista nera dei token).** L'elenco dei refresh token revocati, consultato a ogni rinnovo. In MusicStudio è l'app `token_blacklist` di simplejwt.

**X-Forwarded-For.** L'header HTTP in cui ogni proxy aggiunge in fondo l'indirizzo da cui ha ricevuto la connessione. I valori a sinistra li può scrivere il client, quindi si legge contando da destra.

**Content-Security-Policy (CSP).** Un'intestazione HTTP che dice al browser da dove la pagina può caricare script, stili e immagini, e verso dove può connettersi. È la seconda linea di difesa contro l'XSS.

**CORS (Cross-Origin Resource Sharing).** Le regole con cui un server dice al browser quali altri siti possono chiamarlo. Le nostre API accettano chiamate dal browser solo dall'origine del portale.

**httpOnly cookie.** Un cookie che il JavaScript della pagina non può leggere. È il posto più sicuro per un refresh token nel browser, ed è il nostro passo successivo.

**nginx-unprivileged.** La variante dell'immagine di nginx che gira con un utente normale, non come amministratore, e ascolta sulla porta 8080.

**Route fallback (fallback delle rotte).** In una SPA, rispondere con `index.html` a ogni percorso che non è un file, così il router del client mostra la pagina giusta anche dopo un ricaricamento.

**SPA (Single-Page Application).** Un'applicazione web che il browser scarica una volta e che poi cambia pagina con JavaScript, chiamando le API per i dati.

**Web Locks API.** Un'API del browser che permette a più schede della stessa origine di fare un'operazione una alla volta. La usiamo perché due schede non rinnovino insieme lo stesso refresh token.

**XSS (Cross-Site Scripting).** Uno script estraneo che gira nella pagina con i poteri dell'utente.

## Termini aggiunti nella fase 7

**Account lockout (blocco dell'account).** Dopo un certo numero di password sbagliate di fila l'account si rifiuta di far entrare per un po'. Da noi: cinque errori, 15 minuti, poi il doppio a ogni blocco, fino a 24 ore.

**Anonimizzazione.** Togliere da un dato ciò che identifica una persona (nome, email, note), tenendo il resto (importi e date). Diverso dal cancellare la riga.

**Append-only.** Un registro in cui si aggiunge soltanto: le voci esistenti non si modificano e non si cancellano una per una.

**Audit log.** Il registro di chi ha fatto cosa e quando, per le azioni delicate.

**Consenso.** L'accettazione esplicita di un genitore al trattamento dei dati del figlio, che registriamo con data e versione dell'informativa.

**Enumerazione degli account.** Scoprire quali email sono registrate da come risponde un servizio. Si evita rispondendo sempre allo stesso modo.

**Fernet.** Uno schema di cifratura autenticata della libreria `cryptography`: se un solo byte cambia, la decifratura fallisce.

**GDPR.** Il regolamento europeo sulla protezione dei dati personali. Dà alle persone diritti di accesso, portabilità e cancellazione.

**MFA / verifica in due passaggi.** Oltre alla password serve un secondo elemento, per esempio un codice dal telefono.

**Minimizzazione.** Raccogliere solo i dati che servono davvero. Per questo non chiediamo la data di nascita.

**MultiFernet.** Un portachiavi di chiavi Fernet: la prima cifra, tutte decifrano. Permette di ruotare le chiavi.

**PII (dati personali).** Nome, email e ogni dato che identifica una persona. Non devono finire nei log.

**Retention (conservazione).** Per quanto tempo si tengono i dati prima di cancellarli o anonimizzarli.

**TOTP.** Il codice di sei cifre che cambia ogni 30 secondi, calcolato da un segreto e dall'ora (RFC 6238).
