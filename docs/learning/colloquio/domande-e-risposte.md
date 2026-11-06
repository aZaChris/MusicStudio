# Domande da colloquio su MusicStudio

Domande realistiche su ciò che è stato costruito, con una risposta modello e il punto debole da conoscere. Il punto debole è la domanda successiva che un buon intervistatore farebbe: preparati a quella. Aggiornato alla fine della fase 2.

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

**Punto debole.** Il client è identificato per IP. Dietro un proxy va verificato che l'IP reale arrivi correttamente, altrimenti tutti condividono lo stesso contatore. Non è ancora verificato su Coolify.

### 7. Cosa manca alla sicurezza dell'autenticazione?

**Risposta modello.** Il refresh token ruota, ma i vecchi token non vengono messi in blacklist, quindi restano validi fino alla scadenza. Non c'è logout lato server né MFA. Sono nella lista OWASP come rischi parziali.

**Punto debole.** È una domanda di onestà: non fingere che sia tutto coperto.

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

### 11. Come funzionano i promemoria e cosa succede se due esecuzioni si sovrappongono?

**Risposta modello.** Celery Beat lancia il task ogni 15 minuti. Il task cerca le lezioni tra 23 ore e 45 minuti e 24 ore. Per ognuna fa un `UPDATE` condizionale che la reclama: solo un'esecuzione vince, e solo quella manda le email. È una consegna at-most-once.

**Punto debole.** Se il worker muore tra il claim e l'invio, il promemoria è perso. L'ho scelto consapevolmente, perché un'email mancata è meglio di uno spam ripetuto. La soluzione completa, una outbox con retry e deduplica, è prevista nella fase 3.

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

**Punto debole.** No, il ripristino non è ancora stato provato, e i backup stanno sullo stesso server del database. Entrambe le cose sono nel piano della fase 4. Dillo subito: è meglio che farselo scoprire.

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

## Domanda finale tipica

### 19. Cosa faresti diversamente o cosa miglioreresti per primo?

**Risposta modello.** Per prima cosa proverei davvero il deploy con Docker e il ripristino di un backup, perché sono le due cose non ancora verificate. Poi aggiungerei la revoca dei token. E valuterei la Row Level Security di PostgreSQL, per avere l'isolamento tra studi garantito anche dal database e non solo dal codice.

**Punto debole.** Nessuno: è una domanda che premia l'onestà. Mostra che conosci i limiti di quello che hai costruito.
