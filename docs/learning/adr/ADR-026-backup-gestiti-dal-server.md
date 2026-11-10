# ADR-026: I backup del database li gestisce chi amministra il server

- Stato: accettato
- Data: 2026-11-10

## Contesto

Lo stack aveva i suoi servizi di backup: `backup`, un `pg_dump` giornaliero con rotazione (ADR-005), e `offsite`, che copiava i dump cifrati su un bucket (ADR-020). Nella review prima del deploy, l'amico che ospita MusicStudio sul suo server ha approvato tutto tranne questa parte: i backup della sua macchina li gestisce già lui, con i suoi strumenti.

Due sistemi di backup sullo stesso database vuol dire doppio spazio, doppie credenziali e il dubbio su quale dei due ripristinare in caso di problemi.

## Decisione

- `backup` e `offsite` escono da `docker-compose.coolify.yml`: il deploy su Coolify non li avvia più.
- Restano in un file **opzionale**, `docker-compose.backup.yml`, da sovrapporre al compose principale solo su un server senza un suo sistema di backup.
- Con chi amministra il server si concordano tre cose, scritte nel runbook: una copia **coerente** del database (un `pg_dump` o uno snapshot atomico, non la copia dei file di un PostgreSQL acceso), conservata fuori dal server e cifrata, e una **prova di ripristino** registrata.
- `scripts/restore-drill.sh` resta lo strumento per provare un dump, chiunque lo produca.
- I test di guardia sul compose valgono anche per il file opzionale (nessuna porta, healthcheck ovunque), e un test controlla che i backup non tornino per sbaglio nel deploy.

## Alternative scartate

- **Tenere entrambi i sistemi**: doppio costo e doppia responsabilità, senza un vantaggio chiaro.
- **Cancellare i servizi di backup**: il lavoro e la prova fatta resterebbero solo nella storia di git. Un file opzionale costa poco e serve se il progetto cambia server.

## Conseguenze

- La protezione dei dati dipende da un sistema che non sta nel repository. Per questo la prova di ripristino da un backup vero resta un compito aperto, da fare in staging.
- Le variabili `BACKUP_*` e `RCLONE_*` servono solo con il file opzionale.
- L'ADR-020 resta valido per chi usa il file opzionale.
