# ADR-005: Backup PostgreSQL con un servizio sidecar

- Stato: accettato
- Data: 2026-11-06

## Contesto

Le linee guida chiedono un backup schedulato di PostgreSQL. Il database vive dentro il file Compose dell'applicazione.

## Decisione

Un servizio `backup` con l'immagine `prodrigestivill/postgres-backup-local:16`:

- `pg_dump` compresso ogni giorno (`BACKUP_SCHEDULE=@daily`);
- conserva 7 backup giornalieri, 4 settimanali e 6 mensili;
- scrive nel volume `db-backups` (`/backups/daily`, `weekly`, `monthly`);
- espone un healthcheck HTTP sulla porta 8080 interna.

## Alternative scartate

- **Backup schedulati di Coolify**: esistono, ma per i database creati come risorse separate in Coolify, non per un database definito dentro il nostro Compose.
- **Database come risorsa separata in Coolify**: possibile, ma la configurazione uscirebbe dal repository.
- **cron sull'host**: non versionato con l'applicazione e non visibile in Coolify.
- **WAL archiving e point-in-time recovery**: perdita di dati quasi nulla, ma molto più complesso. Lo valuteremo nella fase 4 se servirà.

## Conseguenze

- I backup stanno **sullo stesso server** del database. Proteggono da errori umani e corruzione, non dalla perdita del server. La copia off-site è un compito della fase 4.
- Nel caso peggiore perdiamo fino a 24 ore di dati.
- Un backup che non è mai stato ripristinato non è un backup: la prova di restore è nel piano della fase 4.
- Il tag `:16` dell'immagine è "mobile" (segue le patch). Fissarlo a un digest è un miglioramento della fase 4.
