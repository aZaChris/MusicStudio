# Domande da colloquio su MusicStudio

Domande realistiche su ciò che è stato costruito, con una risposta modello e il punto debole da conoscere. Il punto debole è la domanda successiva che un buon intervistatore farebbe: preparati a quella. Aggiornato alla fine della fase 3.

## Architettura

### 1. Descrivimi l'architettura del backend.

**Risposta modello.** È un monolite modulare in Django e DRF: un solo deploy, un'app per ogni dominio (allievi, lezioni, pacchetti, pagamenti e così via). Dentro ogni app le scritture stanno in `services.py` e le letture complesse in `selectors.py`, mentre view e serializer sono sottili. Il database è PostgreSQL, i task in background girano su Celery con Redis. Tutto è in container Docker con un deploy su Coolify.

**Punto debole.** "Perché non microservizi?" Rispondi con la scala: dieci insegnanti per studio, nessun bisogno di scalare i domini in modo indipendente, e i microservizi aggiungerebbero rete, deploy multipli e consistenza distribuita. Ammetti che il confine tra moduli è una convenzione, non un vincolo tecnico.

### 2. Perché un service layer? Django non lo richiede.

**Risposta modello.** Perché la logica era sparsa tra modelli, serializer e view, e le property facevano query nascoste. Con i service ogni regola sta in un punto solo, si testa senza HTTP e si riusa da Celery e dall'admin. Spostando la logica è emerso anche un bug di concorrenza nel completamento delle lezioni.

**Punto debole.** È una convenzione: niente impedisce di rimettere logica in una view. Si regge su review e sulla constitution.

### 3. Come gestisci gli errori di validazione nei service?

**Risposta modello.** I service sollevano la `ValidationError` di Django, così non dipendono da DRF. Un exception handler personalizzato la converte in una risposta 400 con lo stesso formato degli errori dei serializer.

**Punto debole.** Due tipi di errore di validazione nel progetto possono confondere. Va spiegato bene a chi entra nel team.

## Sicurezza

### 4. Come garantisci che un insegnante non veda i dati di un altro?

**Risposta modello.** Il tenant è lo studio, obbligatorio per ogni insegnante e allievo. A ogni richiesta calcolo una volta un contesto con ruolo e studio, e ogni queryset passa da una funzione di scoping che lo usa. Un oggetto di un altro tenant restituisce 404, non 403, per non rivelarne l'esistenza. E dalla fase 1 lo stesso filtro si applica ai campi di relazione nelle scritture.

**Punto debole.** Prima della fase 1 le scritture non erano protette: un insegnante poteva creare lezioni sugli allievi di un altro. Raccontalo come una scoperta del tuo audit, con il test che lo dimostrava.

### 5. Hai trovato una falla. Come l'hai scoperta e corretta?

**Risposta modello.** Durante l'audit ho notato che i serializer validavano l'id dell'allievo contro tutta la tabella. Ho scritto un test temporaneo: un insegnante crea una lezione sull'allievo di un altro, risposta 201. La correzione è un mixin che restringe a ogni richiesta il queryset dei campi `student` e `package`. Poi un test di regressione per ogni endpoint di scrittura, che controlla anche che nel database non arrivi niente.

**Punto debole.** "E se domani aggiungi un nuovo campo di relazione?" Il mixin copre solo `student` e `package`. Un nuovo campo va aggiunto alla mappa, e il test cross-tenant della nuova feature è l'unica garanzia.

### 6. Come proteggi il login dal brute force?

**Risposta modello.** Con un throttle DRF dedicato: 5 tentativi al minuto per client, configurabile da variabile d'ambiente. I contatori stanno in Redis, così sono condivisi tra tutti i processi gunicorn.

**Punto debole.** Il client è identificato per IP, e fino alla fase 4 questo era un buco vero: DRF, senza l'impostazione `NUM_PROXIES`, usava come identità tutto l'header `X-Forwarded-For`, che scrive il client. Cambiandolo a ogni tentativo si aggirava il limite. Ora `NUM_PROXIES` segue il numero di proxy fidati, e un test prova proprio l'attacco. Durante un guasto di Redis il limite non c'è, per scelta.

### 7. Cosa manca alla sicurezza dell'autenticazione?

**Risposta modello.** Dalla fase 4, poco: il refresh token ruota e quello vecchio va nella lista nera, il logout spegne il token del dispositivo, e un operatore può chiudere tutte le sessioni di un account. Manca l'autenticazione a due fattori.

**Punto debole.** I token di accesso non sono nella lista nera: dopo il logout funzionano ancora per al massimo 15 minuti. È un compromesso voluto, per non fare una query a ogni richiesta. Dillo tu, prima che te lo chiedano.

## Database e performance

### 8. Cos'è il problema N+1 e dove l'hai trovato?

**Risposta modello.** È una query per la lista più una per ogni elemento. L'elenco degli allievi faceva 22 query con 10 allievi, perché il serializer chiedeva pacchetto attivo e ultimo pagamento per ognuno. L'ho risolto con un `Prefetch` filtrato e una `Subquery` annotata: ora sono 4 query fisse. Un test confronta 1 e 25 righe e blocca le regressioni.

**Punto debole.** "Quattro query non è il minimo." Vero: si potrebbe fare tutto con una query più complessa. Ma la leggibilità conta, e il numero è costante.

### 9. Come hai scelto gli indici?

**Risposta modello.** Solo per le query frequenti, misurate con `EXPLAIN ANALYZE` su 200.000 lezioni. Un indice composto `(teacher_id, start_time)` per l'agenda e un indice parziale per i promemoria non inviati. Ho anche scoperto che il filtro `__date` di Django impediva di usare l'indice: con un intervallo di datetime i blocchi letti sono scesi da 1.000 a 20.

**Punto debole.** Gli indici sono stati creati con migrazioni normali, che bloccano le scritture. Su tabelle grandi in produzione servirebbe `AddIndexConcurrently`.

### 10. Come eviti di scalare due volte lo stesso pacchetto?

**Risposta modello.** `complete_lesson` blocca la riga della lezione con `select_for_update`. Se due richieste arrivano insieme, la seconda aspetta e poi vede lo stato "completata". Il pacchetto si scala con un solo `UPDATE` condizionato su `lessons_remaining > 0`, quindi non va mai sotto zero. C'è anche un vincolo nel database.

**Punto debole.** Il lock dura tutta la transazione. Con operazioni lente dentro la transazione diventerebbe un collo di bottiglia. Qui la transazione è breve.

## Task in background

### 11. Come funzionano i promemoria e cosa succede se un worker muore?

**Risposta modello.** Con una outbox. Ogni 15 minuti lo sweep trova le lezioni tra circa 24 ore e, in una transazione, registra una riga per ogni coppia lezione-genitore, con un vincolo unico: ripeterlo non crea doppioni. Ogni consegna è un task che la reclama con un UPDATE condizionale e un lease di 10 minuti, manda l'email e la segna come inviata; se fallisce, Celery riprova con backoff esponenziale. Se un worker muore, dopo il lease un altro riprende la consegna.

**Punto debole.** È "almeno una volta": se il server SMTP accetta l'email e il worker muore prima di segnarla come inviata, il genitore riceve due email. Con SMTP "esattamente una volta" non esiste. Nella fase 1 avevo scelto il contrario, "al massimo una volta", e perdevo promemoria: l'ADR-015 spiega il cambio.

## Deploy e operazioni

### 12. Come fai il deploy?

**Risposta modello.** Con un file Compose per Coolify. Una sola immagine Docker multi-stage, non root, che fa da web, worker o beat in base all'entrypoint. Nessuna porta pubblicata: il proxy di Coolify instrada per dominio e gestisce HTTPS. Le credenziali le genera Coolify, e le variabili obbligatorie bloccano il deploy se mancano.

**Punto debole.** Il Compose non è stato ancora eseguito con Docker reale: ho provato le impostazioni di produzione con gunicorn, ma il primo `docker compose up` è da fare. E tutto gira su un solo server.

### 13. Che differenza c'è tra i tuoi due health endpoint?

**Risposta modello.** `/health/live/` dice solo che il processo risponde, senza toccare dipendenze. `/health/ready/` controlla PostgreSQL e Redis e risponde 503 se uno manca. Se la liveness controllasse il database, un guasto di un minuto farebbe riavviare tutti i web sani.

**Punto debole.** Il controllo di Celery Beat è indiretto: guarda quando è stato aggiornato il file di schedulazione. Può dare falsi allarmi se il task cambia frequenza.

### 14. Come gestisci la configurazione tra ambienti?

**Risposta modello.** Twelve-Factor: tutto da variabili d'ambiente, documentate in `.env.example`. Settings separati per sviluppo, test e produzione. In produzione i segreti non hanno default, quindi l'app non parte se ne manca uno. Django si fida dell'intestazione `X-Forwarded-Proto` del proxy, altrimenti il redirect HTTPS andrebbe in loop.

**Punto debole.** Nel Dockerfile `collectstatic` ha bisogno delle impostazioni di produzione, e passo valori fittizi solo per quel comando. Funziona, ma va spiegato.

### 15. Come funzionano i backup? Li hai mai ripristinati?

**Risposta modello.** Un servizio sidecar fa un `pg_dump` compresso ogni giorno e tiene 7 copie giornaliere, 4 settimanali e 6 mensili in un volume dedicato. Il RPO è di 24 ore.

**Punto debole.** Dalla fase 4 una copia cifrata va ogni giorno su un bucket fuori dal server, e il ripristino l'ho provato: 78.000 lezioni in 20 secondi, con il conteggio delle righe di ogni tabella. Ma la prova è stata fatta in locale: il download dal bucket vero va ancora provato dopo il primo deploy.

## Qualità

### 16. Come garantisci la qualità del codice?

**Risposta modello.** Una pipeline GitHub Actions a ogni push: ruff, formattazione, mypy, controllo delle migrazioni, 92 test su PostgreSQL e Redis veri con copertura minima del 90%, e lo schema OpenAPI senza avvisi. In locale gli stessi controlli veloci con pre-commit.

**Punto debole.** Il blocco del merge richiede la branch protection su GitHub, che va attivata a mano. E mypy non controlla i test, perché non tipizza factory_boy.

### 17. Come hai fatto un refactoring così ampio senza rompere niente?

**Risposta modello.** I 26 test originali erano la rete di sicurezza. Ho spostato la logica nei service cambiando nei test solo il punto di chiamata, e sono rimasti verdi. Poi ho aggiunto i test per i difetti trovati.

**Punto debole.** I test originali non coprivano le scritture cross-tenant. Una rete di sicurezza copre solo ciò che testa.

### 18. Perché i test non usano SQLite?

**Risposta modello.** Perché uso funzionalità di PostgreSQL che SQLite non ha o gestisce diversamente: indici parziali, `select_for_update`, e nella fase 2 i vincoli di esclusione. Test su un altro database darebbero una falsa sicurezza.

**Punto debole.** I test sono più lenti, circa 13 secondi. È un prezzo che accetto.

## Fase 2: dominio

### 20. Come impedisci due lezioni sovrapposte?

**Risposta modello.** Con due ExclusionConstraint di PostgreSQL, uno per insegnante e uno per allievo, su `tstzrange(inizio, fine, '[)')` con l'operatore di sovrapposizione. Sono parziali: valgono solo per le lezioni programmate o completate. Un controllo nel codice avrebbe una race condition tra lettura e scrittura; il vincolo no. Il service traduce la violazione in un 409.

**Punto debole.** Due inserimenti simultanei possono andare in deadlock sul controllo del vincolo. L'ho scoperto con un test a due thread e lo gestisco riprovando la scrittura: il secondo tentativo riceve una violazione normale.

### 21. Perché hai salvato la fine della lezione invece di calcolarla?

**Risposta modello.** Perché in un indice PostgreSQL accetta solo funzioni immutabili, e `timestamptz + interval` è STABLE: dipende dal fuso orario. L'ho verificato provando a creare il vincolo sull'espressione. L'API continua a usare `duration_minutes`, calcolato dal service.

**Punto debole.** Calcolando la fine in Python su un datetime con il fuso di Roma, la notte del cambio dell'ora una lezione di un'ora ne durava due, perché Python somma sull'orologio locale. Un test sul 25 ottobre l'ha trovato. Ora il calcolo si fa in UTC.

### 22. Come hai implementato la multi-tenancy?

**Risposta modello.** Tabelle condivise con il tenant esplicito: lo studio è obbligatorio per insegnanti e allievi, e un solista ha uno studio personale creato da una migrazione. Il contesto del tenant si calcola con una query per richiesta e si mette in cache sulla richiesta Django, perché con JWT un middleware non conosce ancora l'utente. Ho scartato uno schema per tenant: moltiplica le migrazioni senza un vero beneficio a questa scala.

**Punto debole.** La regola "lo studio dell'allievo è quello del suo insegnante" è garantita dai service, non dal database.

### 23. Che differenza fai tra visibilità e permessi?

**Risposta modello.** La visibilità viene dal queryset filtrato per tenant, e fuori dal proprio studio dà 404. I permessi DRF lavorano su ciò che vedi: `has_permission` controlla il ruolo per l'azione, `has_object_permission` controlla se puoi modificare quell'oggetto. Lo spostamento di un allievo è un'azione solo per il titolare, verso un insegnante dello stesso studio.

**Punto debole.** `has_object_permission` non viene chiamato nelle liste né nella creazione. Lì la protezione è il queryset e la validazione dei campi di relazione.

### 24. Come eviti che lo schema OpenAPI e il codice divergano?

**Risposta modello.** Lo schema è generato dal codice, ma è salvato nel repository. Un test, la CI e un hook pre-commit lo rigenerano e falliscono se è diverso. Così ogni cambio di contratto si vede nel diff della pull request. Un postprocessing hook documenta in un punto solo gli errori di ogni operazione.

**Punto debole.** Le regole che decidono quali errori documentare sono euristiche, basate su metodo e percorso. Un nuovo tipo di conflitto richiede di aggiornarle.

## Fase 3: Celery e pagamenti

### 25. Come gestisci i webhook di Stripe?

**Risposta modello.** Verifico la firma HMAC sul corpo grezzo e rispondo 400 se non è valida. Salvo l'evento con il suo id unico, così un duplicato non fa niente, e rispondo 200 subito. Un task Celery avviato dopo il commit lo elabora in modo idempotente, e un vincolo uno-a-uno tra pagamento e tentativo impedisce il doppio pagamento. Una riconciliazione oraria chiede a Stripe lo stato dei tentativi rimasti aperti.

**Punto debole.** Non ho ancora l'allowlist degli IP di Stripe sul proxy, che sarebbe una difesa in più. E l'integrazione non è stata provata contro una sandbox Stripe reale: i test usano un finto per le chiamate e firme vere per i webhook.

### 26. Come eviti un doppio pagamento se il genitore fa doppio clic?

**Risposta modello.** Il service blocca la riga del pacchetto per tutta l'operazione. La seconda richiesta aspetta, poi trova il tentativo aperto e restituisce lo stesso link. In più, la chiamata a Stripe porta una chiave di idempotenza legata all'UUID del tentativo, così anche i retry di rete dell'SDK non creano una seconda sessione.

**Punto debole.** La riga resta bloccata durante una chiamata di rete. Con volumi alti si separerebbe la chiamata dalla transazione.

### 27. Perché un pagamento "completato" a volte non lo registri?

**Risposta modello.** Perché con i metodi differiti, come l'addebito SEPA, Stripe completa la sessione con `payment_status` "unpaid" e conferma giorni dopo con `async_payment_succeeded`. Registro il pagamento solo quando il denaro c'è, come raccomanda Stripe.

**Punto debole.** Nessuno dal lato del codice; l'errore comune è proprio registrare su ogni `completed`.

### 28. Cosa succede ai task se un worker Celery muore?

**Risposta modello.** Con `acks_late` e `reject_on_worker_lost` il task torna in coda e un altro worker lo riprende. Il prezzo è che può girare due volte, quindi ogni task è idempotente: marcatori di "già fatto" con la riga bloccata, vincoli unici, claim condizionali. Un test fissa queste impostazioni.

**Punto debole.** Il `visibility_timeout` di Redis deve restare più lungo del task più lungo, altrimenti Redis riconsegna un task ancora in esecuzione.

### 29. Come invalidi la cache della dashboard?

**Risposta modello.** Con chiavi versionate per studio. La versione fa parte della chiave, e i segnali `post_save` e `post_delete` la incrementano dopo il commit per ogni scrittura su lezioni, pacchetti, pagamenti e allievi. Così invalido tutte le chiavi dello studio in un colpo e catturo anche l'admin. Una richiesta servita dalla cache costa una query invece di sei.

**Punto debole.** `update()` e `bulk_create()` non inviano segnali. E testando Redis spento ho scoperto che il rate limiting di DRF faceva cadere tutta l'API: ora fallisce aperto, quindi durante un guasto di Redis non c'è rate limiting.

## Fase 4: produzione

### 30. Come fai il logout con i JWT, che non si possono revocare?

**Risposta modello.** Rendo revocabili i refresh token con la lista nera di simplejwt. Ogni refresh usato per rinnovare muore subito, e il logout mette nella lista quello del dispositivo, dopo aver controllato che appartenga all'utente. Un token altrui riceve lo stesso errore di uno malformato, così l'endpoint non fa da oracolo. Un task giornaliero cancella i token scaduti.

**Punto debole.** Il token di accesso resta valido fino alla scadenza, 15 minuti. Abbassarne la durata è il prezzo per non controllarlo a ogni richiesta.

### 31. Come colleghi i log di una richiesta a quelli dei task Celery che ha avviato?

**Risposta modello.** Con un request id. Un middleware lo crea, o lo riusa dal proxy se è sicuro, lo mette in una ContextVar e lo restituisce nella risposta. Un filtro lo aggiunge a ogni riga di log, e un segnale di Celery lo copia negli header del messaggio del task. In produzione i log sono JSON, una riga per evento.

**Punto debole.** All'inizio la riga di errore di Django perdeva l'id, perché viene scritta dopo la fine dei middleware. L'ho scoperto solo provando con gunicorn vero, e ora l'id si azzera alla chiusura della risposta.

### 32. Come eviti che Sentry riceva dati personali?

**Risposta modello.** `send_default_pii=False` e un hook `before_send` che toglie gli header con credenziali, i cookie, i corpi degli endpoint di login e webhook, e sostituisce le email nei messaggi. Restano solo request id, studio e utente come identificativi. Sentry è attivo solo se c'è il DSN: senza, l'API funziona uguale.

**Punto debole.** La pulizia si basa su regole: un dato personale in un campo che non ho previsto passerebbe. Va rivisto quando cambiano i dati.

### 33. Quanto regge la tua API?

**Risposta modello.** Con Locust, 50 insegnanti simulati su 78.000 lezioni: zero errori e un p95 delle letture tra 62 e 560 millisecondi, su due run. La scoperta è stata il login: l'hash PBKDF2 costa circa 2 secondi di CPU su quella macchina, quindi una raffica di login satura i 3 worker.

**Punto debole.** Misurato su un portatile, con client e server sulla stessa CPU e senza Redis, e con una grande differenza tra i due run. Sono numeri per trovare problemi, non promesse: vanno rifatti sul server.

### 34. Come leggi l'IP del client dietro un proxy?

**Risposta modello.** Da `X-Forwarded-For`, contando da destra quanti proxy fidati ci sono, perché ogni proxy aggiunge in fondo. Il primo valore lo scrive il client e non va mai usato. Una sola impostazione, `TRUSTED_PROXY_COUNT`, guida sia l'allowlist del webhook di Stripe sia i limiti di rate di DRF.

**Punto debole.** Se l'infrastruttura cambia, per esempio aggiungendo Cloudflare, il numero va cambiato. Sbagliarlo per eccesso ridà al client il controllo del suo IP.

## Domanda finale tipica

### 19. Cosa faresti diversamente o cosa miglioreresti per primo?

**Risposta modello.** Per prima cosa farei il deploy reale su Coolify e il ripristino dal bucket vero, perché sono le due cose provate solo in locale. Poi rifarei il load test sul server, per avere numeri credibili. E valuterei la Row Level Security di PostgreSQL, per avere l'isolamento tra studi garantito anche dal database e non solo dal codice.

**Punto debole.** Nessuno: è una domanda che premia l'onestà. Mostra che conosci i limiti di quello che hai costruito.
