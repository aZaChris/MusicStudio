# Docker e deploy con Coolify

## TL;DR

Docker impacchetta l'applicazione e le sue dipendenze in un'immagine che gira uguale ovunque. Docker Compose descrive più container che lavorano insieme. Coolify è una piattaforma self-hosted che prende un file Compose da un repository Git e lo mette in produzione, con dominio, HTTPS e variabili d'ambiente. In MusicStudio abbiamo sostituito il deploy AWS con un file Compose per Coolify: nessuna porta pubblicata, healthcheck ovunque, credenziali generate e backup schedulato.

## Il problema reale

Il progetto aveva un Compose di sviluppo e una guida per AWS ECS. Tre problemi.

Primo: le linee guida vietano AWS. Per un progetto di questa dimensione, ECS con RDS ed ElastiCache è anche costoso e complicato.

Secondo: il Compose di sviluppo non era mai stato provato davvero, e infatti non poteva funzionare. Montava il codice sorgente su `/app`, ma il Dockerfile creava il virtualenv in `/app/.venv`. Il mount copriva la cartella dell'immagine e il virtualenv spariva. Il container non avrebbe trovato nemmeno Django.

Terzo: l'immagine non era adatta alla produzione. Girava come root, usava `uv:latest` (quindi build non riproducibili), non aveva healthcheck, e il backend usava il server di sviluppo `runserver`.

## Come funziona

Pensa ai container delle navi. Prima dei container, ogni merce aveva la sua forma, e caricare una nave era un rompicapo. Con il container standard, la gru non sa cosa c'è dentro: sposta una scatola di forma nota. Un'immagine Docker è la scatola: dentro c'è l'applicazione con tutto quello che le serve. Il server, come la gru, sa solo come avviarla.

Alcuni concetti chiave.

**Multi-stage build.** Il Dockerfile ha più fasi. La prima, il builder, ha gli strumenti per installare le dipendenze. La fase finale copia solo il risultato. L'immagine finale è più piccola e contiene meno software, quindi meno superficie di attacco.

**Utente non root.** Se qualcuno sfrutta una vulnerabilità dell'applicazione, si ritrova con i permessi di un utente limitato, non di amministratore del container.

**Compose.** Un file YAML che descrive servizi, volumi, reti e dipendenze. `depends_on` con `condition: service_healthy` dice "avvia questo servizio solo quando quell'altro è sano".

**Coolify.** È come un piccolo Heroku installato sul tuo server. Ha un reverse proxy che riceve il traffico HTTPS e lo inoltra al container giusto in base al dominio. Ha alcune convenzioni proprie:

- le variabili `SERVICE_USER_*` e `SERVICE_PASSWORD_*` vengono generate da Coolify e conservate tra un deploy e l'altro;
- `${VAR:?}` rende obbligatoria una variabile, e Coolify blocca il deploy finché non la imposti;
- il dominio si assegna a un servizio, con un suffisso di porta, per esempio `https://api.example.com:8000`, dove 8000 è la porta interna del container.

La documentazione di Coolify dice anche di non usare `ports:`: una porta pubblicata sull'host scavalca il proxy.

## Come lo abbiamo applicato in MusicStudio

**L'immagine** è in `backend/Dockerfile`. Due fasi. Il builder usa `uv` fissato alla versione 0.12.7, installa le dipendenze dal lockfile in `/opt/venv` (fuori da `/app`, così il mount di sviluppo non la nasconde più) ed esegue `collectstatic`. La fase finale crea l'utente `app`, copia il virtualenv e il codice, e definisce un `HEALTHCHECK`.

**Un'immagine, tre ruoli.** Lo script `backend/docker/entrypoint.sh` legge il primo argomento:

```sh
case "$role" in
  web)    python manage.py migrate --noinput   # se RUN_MIGRATIONS=1
          exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" ... ;;
  worker) exec celery -A config worker ... ;;
  beat)   exec celery -A config beat --schedule /tmp/celerybeat-schedule ... ;;
esac
```

`exec` fa sì che gunicorn o Celery diventino il processo principale del container, e ricevano i segnali di arresto da Docker.

**Sviluppo**: `docker-compose.yml` nella radice. Database, Redis, backend con `runserver` e ricarica automatica, worker e beat. Le porte sono pubblicate, ma configurabili. Il frontend React, fuori scope, parte solo con `--profile frontend`, così il backend non ha bisogno di Node.

**Produzione**: `docker-compose.coolify.yml`. Database, Redis, backend, worker, beat e backup. Nessun `ports:`. Le credenziali del database e le chiavi segrete sono variabili magiche di Coolify. Le impostazioni SMTP sono obbligatorie con `${SMTP_HOST:?}`. Gli host ammessi da Django hanno come default il dominio assegnato da Coolify (`SERVICE_FQDN_BACKEND_8000`).

**Le migrazioni** le esegue il container web all'avvio. Con una sola replica è sicuro e semplice. Con più repliche partirebbero in parallelo, quindi la variabile `RUN_MIGRATIONS=0` permette di spostarle in un comando separato.

**Cosa ho verificato e cosa no.** Docker non è disponibile in questo ambiente di lavoro. Ho validato la sintassi dei due file Compose e controllato che ogni servizio abbia un healthcheck e che il file di Coolify non pubblichi porte. Ho avviato gunicorn con le impostazioni di produzione senza Docker e ho provato lo script di healthcheck. Ma un `docker compose up` reale non è stato eseguito: è il primo controllo da fare.

## Alternative considerate

**AWS ECS con RDS.** Vietato, e sproporzionato.

**Kubernetes.** Potente, ma per tre processi e un database è troppa infrastruttura da gestire.

**Il build pack "Dockerfile" di Coolify.** Gestisce un solo container: niente worker, beat o backup.

**Un servizio separato per le migrazioni.** Più pulito, ma il comportamento di Coolify con i servizi "one-shot" non è documentato chiaramente. Nella fase 4 non l'abbiamo cambiato: senza un deploy reale su cui provarlo, restano le migrazioni all'avvio del web.

**Ancore YAML** per non ripetere l'ambiente di worker e beat. Le uso nel Compose di sviluppo. Nel file di Coolify no, perché il suo parser ha avuto problemi con le ancore. È una scelta prudente, che costa un po' di duplicazione.

## Errori comuni e trade-off

- **Montare il codice sopra il virtualenv.** È esattamente il bug che avevamo.
- **Usare tag `latest`.** La build di domani può essere diversa da quella di oggi.
- **Pubblicare le porte di database e Redis in produzione.** Li espone a Internet.
- **`runserver` in produzione.** È un server di sviluppo: un solo processo, non pensato per carico e sicurezza.
- **Trade-off:** tutto gira su un solo server. Se il server cade, cade tutto. Per questo prodotto è accettabile, ma va detto.
- **Trade-off:** Redis non ha password, perché è raggiungibile solo dalla rete interna. Se un giorno fosse esposto, servirebbe.

## Come lo spiegheresti a un colloquio

Ho un Dockerfile multi-stage con utente non root e versioni fissate, e una sola immagine che fa da web, worker e beat in base all'argomento dell'entrypoint. Il deploy è un file Compose per Coolify, una piattaforma self-hosted: nessuna porta pubblicata, perché il proxy di Coolify instrada per dominio, e ogni servizio ha un healthcheck. Le credenziali le genera Coolify, e le variabili obbligatorie bloccano il deploy se mancano. Lo sviluppo usa un Compose separato con ricarica automatica. Ho anche trovato che il vecchio Compose non poteva funzionare, perché il mount del sorgente nascondeva il virtualenv.

## Domande di autoverifica

1. **Perché il virtualenv sta in `/opt/venv` e non in `/app/.venv`?**
   Perché in sviluppo il codice è montato su `/app`, e il mount nasconderebbe il virtualenv creato nell'immagine.

2. **Perché nel file di Coolify non ci sono `ports:`?**
   Perché il proxy di Coolify instrada il traffico per dominio. Una porta pubblicata scavalcherebbe il proxy ed esporrebbe il servizio direttamente.

3. **A cosa serve `exec` nell'entrypoint?**
   A sostituire lo script con il processo vero, che così riceve i segnali di arresto e si chiude in modo pulito.

4. **Perché le migrazioni all'avvio sono sicure solo con una replica?**
   Con più repliche, più container proverebbero a migrare nello stesso momento.

5. **Cosa significa `${SMTP_HOST:?}` per Coolify?**
   Che la variabile è obbligatoria: Coolify la evidenzia e blocca il deploy finché non ha un valore.
