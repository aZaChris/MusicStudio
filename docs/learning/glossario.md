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

**Celery.** Una libreria Python per eseguire task in background, fuori dalle richieste HTTP.

**Celery Beat.** Il processo di Celery che lancia i task a orari prestabiliti, come un cron.

**CI (Continuous Integration).** Un sistema che a ogni push controlla automaticamente il codice: lint, test, build.

**Claim (reclamare).** Segnare un lavoro come "preso" in modo atomico, così che un altro processo non lo faccia di nuovo. Noi lo facciamo con un `UPDATE ... WHERE reminder_sent_at IS NULL`.

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

**Liveness probe.** Il controllo "il processo è vivo?". Se fallisce, il container va riavviato.

**Lockfile.** Il file che fissa le versioni esatte di tutte le dipendenze (`uv.lock`), per installazioni identiche ovunque.

**Migration (migrazione).** Un file che descrive una modifica allo schema del database, applicata con `migrate`.

**Modular monolith (monolite modulare).** Un'unica applicazione deployabile, divisa all'interno in moduli per dominio con confini chiari.

**Multi-stage build.** Un Dockerfile con più fasi: una per costruire, una finale più piccola con solo il necessario.

**Multi-tenancy.** Un solo sistema che serve più clienti separati (tenant), ognuno con i propri dati isolati.

**mypy.** Lo strumento che controlla i tipi in Python senza eseguire il codice.

**N+1 query problem.** Una query per la lista, più una query per ogni elemento. Fa crescere il lavoro del database con i dati.

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

**RPO / RTO.** Recovery Point Objective: quanti dati puoi perdere. Recovery Time Objective: quanto tempo serve per ripartire.

**ruff.** Uno strumento molto veloce per lint e formattazione del codice Python.

**Scoping.** Restringere un queryset ai soli dati che un utente può vedere.

**`select_for_update`.** Blocca le righe lette fino alla fine della transazione, così nessun altro le modifica nel frattempo.

**`select_related`.** Carica gli oggetti collegati "verso uno" nella stessa query, con una JOIN.

**Selector.** Nel nostro codice, una funzione di lettura che restituisce un queryset già filtrato e ottimizzato.

**Serializer.** In DRF, la classe che valida i dati in ingresso e trasforma gli oggetti in JSON.

**Service layer.** Lo strato di funzioni che contiene le operazioni di business di scrittura.

**Sidecar.** Un container di supporto accanto a quello principale, come il nostro servizio di backup.

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
