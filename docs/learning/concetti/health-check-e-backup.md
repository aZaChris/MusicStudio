# Health check e backup

## TL;DR

Un health check è un controllo automatico che dice se un servizio funziona. Ne abbiamo due tipi: liveness ("il processo risponde?") e readiness ("può servire richieste, cioè database e Redis rispondono?"). Ogni servizio del Compose ha il suo controllo. Il backup è una copia periodica del database: un servizio dedicato fa un `pg_dump` ogni giorno e conserva 7 copie giornaliere, 4 settimanali e 6 mensili. Il punto debole, da conoscere: i backup stanno sullo stesso server.

## Il problema reale

Un container "acceso" non è un container che funziona. Il processo può essere vivo ma bloccato. Può aver perso la connessione al database. Può essere ancora in fase di avvio. Senza un controllo esplicito, Docker e Coolify non hanno modo di saperlo, e il proxy continua a mandare traffico a un servizio che risponde con errori.

Prima di questo lavoro, solo il database aveva un controllo di salute. Backend, worker e beat no. E non esisteva un endpoint pensato per questo.

Il backup è il problema opposto: non riguarda il "funziona adesso?" ma il "possiamo tornare indietro?". Un comando sbagliato, una migrazione difettosa, un disco corrotto. Senza una copia, i dati dei clienti sono persi per sempre. Il progetto non aveva nessun backup.

## Come funziona

Pensa a un medico. La liveness è controllare se il paziente respira. La readiness è controllare se è in grado di tornare al lavoro. Sono domande diverse con conseguenze diverse. Se non respira, intervieni subito. Se respira ma ha la febbre, non lo mandi al lavoro, ma non lo rianimi.

Nei sistemi in container vale lo stesso.

**Liveness.** Il processo risponde? Se no, è bloccato, e ha senso riavviarlo. Questo controllo non deve toccare le dipendenze esterne. Se il database ha un problema di un minuto e la liveness controllasse il database, l'orchestratore riavvierebbe tutti i container web: sono sani, ma il controllo direbbe il contrario. Un guasto piccolo diventerebbe grande.

**Readiness.** Il servizio può gestire richieste? Qui si controllano le dipendenze. Se fallisce, il servizio non deve ricevere traffico, ma non serve riavviarlo.

**Backup logico con pg_dump.** `pg_dump` esporta il database in un file, come una fotografia del contenuto. La rotazione decide quante fotografie tenere: le ultime 7 giornaliere, una a settimana per 4 settimane, una al mese per 6 mesi. È lo schema "nonno-padre-figlio".

**RPO e RTO.** Il Recovery Point Objective è quanti dati puoi permetterti di perdere: con un backup giornaliero, fino a 24 ore. Il Recovery Time Objective è quanto tempo serve per tornare operativi.

## Come lo abbiamo applicato in MusicStudio

**Gli endpoint** sono in `backend/config/health.py`:

- `GET /health/live/` risponde `{"status": "ok"}` senza toccare niente.
- `GET /health/ready/` esegue `SELECT 1` su PostgreSQL e `PING` su Redis. Se tutto va, risponde 200. Se qualcosa fallisce, risponde 503 indicando quale controllo.

```python
CHECKS: dict[str, Callable[[], None]] = {"database": check_database, "redis": check_redis}

def ready(request: HttpRequest) -> JsonResponse:
    results = {}
    for name, check in CHECKS.items():
        try:
            check(); results[name] = "ok"
        except Exception:
            logger.exception("Readiness check %s failed", name); results[name] = "error"
    ...
```

Gli endpoint non richiedono autenticazione, non hanno limiti di frequenza e sono esclusi dal redirect HTTPS. Non rivelano dettagli: solo `ok` o `error`.

**Il probe** è `backend/docker/healthcheck.py`, uno script della libreria standard, perché l'immagine slim non contiene curl. Ha due modalità: `http`, che chiama un endpoint locale, e `beat`, che controlla quando è stato aggiornato l'ultima volta il file di schedulazione di Celery Beat.

**I controlli per servizio**, nel file `docker-compose.coolify.yml`:

- **db**: `pg_isready`.
- **redis**: `redis-cli ping`.
- **backend**: lo script sulla readiness, perché Coolify usa lo stato di salute per decidere se un deploy è riuscito. Il `HEALTHCHECK` del Dockerfile usa invece la liveness.
- **worker**: `celery inspect ping` verso il proprio nodo.
- **beat**: il file di schedulazione deve essere stato aggiornato negli ultimi 20 minuti. Beat lo riscrive dopo ogni invio, e il task gira ogni 15 minuti. È un controllo indiretto: lo dico apertamente, ma è meglio di niente.
- **backup**: il controllo HTTP che l'immagine espone sulla porta 8080.

**Le verifiche.** I test in `backend/config/tests/test_health.py` simulano database e Redis non raggiungibili e controllano il 503. Con gunicorn e le impostazioni di produzione, senza Redis avviato, ho ottenuto liveness 200 e readiness 503, come previsto.

**Il backup** è il servizio `backup` con l'immagine `prodrigestivill/postgres-backup-local:16`. Scrive nel volume `db-backups`, nelle cartelle `daily`, `weekly` e `monthly`.

**Ripristino**, in breve: si sceglie un file in `/backups/daily`, si ferma il backend, poi si ricarica il dump nel database con `gunzip -c file.sql.gz | psql`, e si riavvia. La procedura completa, con una prova reale, è un compito della fase 4.

## Alternative considerate

**Un solo endpoint di salute** che controlla tutto. Più semplice, ma trasforma un guasto del database in un riavvio a catena dei web.

**La libreria django-health-check.** Completa e configurabile. Per due controlli è una dipendenza in più.

**I backup integrati di Coolify.** Funzionano per i database creati come risorse separate in Coolify, non per un database definito dentro il nostro Compose.

**Cron sull'host del server.** Funziona, ma non è versionato con l'applicazione e non si vede in Coolify.

**WAL archiving per il point-in-time recovery.** Permette di tornare a qualsiasi secondo, non solo all'ultimo dump. È molto più complesso. Lo valuteremo nella fase 4 se il prodotto ne avrà bisogno.

## Errori comuni e trade-off

- **Liveness che controlla il database.** Causa riavvii a catena durante un guasto esterno.
- **Health check troppo pesanti.** Se fanno query costose ogni 10 secondi, diventano loro stessi un carico.
- **Endpoint di salute che rivelano versioni o stack trace.** Sono pubblici: devono dire solo "ok" o "errore".
- **Backup mai ripristinati.** Un backup non provato è una speranza, non un backup.
- **Backup sullo stesso server dei dati.** È il nostro punto debole attuale: protegge da errori umani e corruzione, non dalla perdita del server. Serve una copia off-site, nella fase 4.
- **Trade-off:** Docker da solo non riavvia un container "unhealthy". Lo segnala. Il riavvio dipende dalla politica dell'orchestratore.

## Come lo spiegheresti a un colloquio

Ho separato liveness e readiness. La liveness dice solo che il processo risponde, quindi un guasto del database non fa riavviare container web sani. La readiness controlla PostgreSQL e Redis e restituisce 503 se uno manca, così il traffico non arriva a un'istanza che non può servirlo. Ogni servizio del Compose ha il suo controllo, anche worker e beat. Per i dati c'è un servizio di backup con `pg_dump` giornaliero e rotazione 7, 4 e 6. So che i backup sono sullo stesso server, e la copia off-site e la prova di ripristino sono nel piano della fase successiva.

## Domande di autoverifica

1. **Che differenza c'è tra liveness e readiness?**
   La liveness dice se il processo è vivo e va riavviato se fallisce. La readiness dice se può servire richieste, controllando le dipendenze, e se fallisce il servizio smette di ricevere traffico.

2. **Perché la liveness non controlla il database?**
   Per non riavviare container sani quando il problema è esterno, cosa che peggiorerebbe il guasto.

3. **Come controlliamo la salute di Celery Beat?**
   Guardando quando è stato aggiornato il file di schedulazione, che Beat riscrive dopo ogni invio. Se è troppo vecchio, Beat è bloccato.

4. **Qual è il RPO con il nostro backup?**
   Fino a 24 ore di dati, perché il dump è giornaliero.

5. **Qual è il punto debole principale dei backup attuali?**
   Stanno sullo stesso server del database. Se il server si perde, si perdono anche i backup.
