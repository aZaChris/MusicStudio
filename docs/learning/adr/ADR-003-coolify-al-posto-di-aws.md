# ADR-003: Docker Compose su Coolify al posto di AWS

- Stato: accettato
- Data: 2026-11-06

## Contesto

La feature 001 documentava un deploy su AWS ECS Fargate con RDS, ElastiCache ed ECR. Le nuove linee guida vietano AWS e chiedono Docker Compose pronto per Coolify, un PaaS self-hosted. Altri vincoli: nessuna porta fissa sul reverse proxy, variabili d'ambiente per tutto, healthcheck su ogni servizio, backup schedulato.

## Decisione

- Due file Compose nella radice del repository: `docker-compose.yml` per lo sviluppo e `docker-compose.coolify.yml` per la produzione.
- In produzione nessun servizio usa `ports:`. Il dominio si imposta in Coolify sul servizio `backend` (per esempio `https://api.example.com:8000`). Il suffisso indica la porta del container, che arriva dalla variabile `PORT`. La documentazione di Coolify dice che una porta pubblicata scavalca l'instradamento per dominio del proxy.
- Le credenziali del database e le chiavi segrete usano le variabili magiche di Coolify (`SERVICE_USER_POSTGRES`, `SERVICE_PASSWORD_64_DJANGOSECRET`). Coolify le genera e le conserva tra un deploy e l'altro.
- Le variabili obbligatorie usano la sintassi `${VAR:?}`: Coolify blocca il deploy finché non hanno un valore.
- Un'unica immagine backend serve tre ruoli (web, worker, beat), scelti dall'argomento dell'entrypoint.
- Il container web esegue `migrate` all'avvio. È sicuro con una sola replica. Con più repliche si imposta `RUN_MIGRATIONS=0` e si migra con un comando separato.
- Niente ancore YAML nel file di Coolify: il suo parser ha avuto problemi con le ancore. È una scelta prudente, che però duplica l'ambiente di worker e beat.

## Alternative scartate

- **AWS ECS / RDS**: vietato. Inoltre costoso e complesso per questa scala.
- **Kubernetes**: troppa infrastruttura per un monolite con tre processi.
- **Build pack "Dockerfile" di Coolify**: gestisce un solo container, quindi niente worker, beat e backup.
- **Servizio di migrazione one-shot**: più pulito, ma il comportamento di Coolify con `depends_on: service_completed_successfully` non è documentato. Lo rivaluteremo nella fase 4.

## Conseguenze

- Tutto il sistema gira su un solo server Coolify. È un single point of failure, accettabile per il prodotto, ma va detto.
- Database e Redis sono raggiungibili solo dalla rete interna. Redis non ha password per questo motivo.
- Il file di Coolify si può provare anche in locale, impostando a mano le variabili magiche.
- In questo ambiente il Compose non è stato eseguito (manca Docker). La prima verifica reale va fatta prima del deploy.
