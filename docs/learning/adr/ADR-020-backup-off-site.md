# ADR-020: Backup off-site cifrati e prova di ripristino

- Stato: accettato
- Data: 2026-11-09

## Contesto

Dalla fase 1 un sidecar (`postgres-backup-local`) fa un `pg_dump` ogni giorno e tiene 7 copie giornaliere, 4 settimanali e 6 mensili (ADR-005). Ma i dump stanno in un volume **sullo stesso server** del database. Se il server si rompe, viene cancellato o compromesso, i backup spariscono insieme ai dati. E nessuno aveva mai provato a ripristinarne uno.

## Decisione

- **Un secondo sidecar, `offsite`**, con l'immagine ufficiale di rclone. Una volta al giorno copia i dump in un bucket S3-compatibile che non sia AWS (per esempio Backblaze B2, Cloudflare R2, Hetzner).
- **Cifratura lato client** con il remote `crypt` di rclone. Il provider vede solo file cifrati, anche nei nomi. Le due password si generano una volta e vanno conservate anche fuori dal server.
- **`rclone copy`, non `sync`.** `sync` rende il bucket identico al volume locale: se il volume venisse svuotato, per errore o da un attaccante, alla copia successiva si svuoterebbe anche il bucket. `copy` non cancella mai niente. Le copie remote più vecchie di 190 giorni (poco più della conservazione mensile) vengono cancellate per età, con `rclone delete --min-age`.
- **Allarme.** Se una copia fallisce, il container chiama l'URL opzionale `BACKUP_ALERT_URL`, per esempio un controllo di healthchecks.io, che manda un'email. L'healthcheck del container diventa "unhealthy" se l'ultima copia riuscita ha più di 26 ore.
- **Dump portabili.** Il sidecar ora usa `--no-owner --no-privileges`, così un dump si ripristina con qualunque utente PostgreSQL.
- **Prova di ripristino** con `scripts/restore-drill.sh`. Lo script ripristina in un database nuovo e confronta il numero di righe di ogni tabella con le righe contenute nel dump stesso: il dump è la fotografia, quindi non serve un file di conteggi separato. Poi controlla che lo schema sia allineato alle migrazioni del codice e stampa i tempi. Ogni prova si registra in `docs/operations/restore-drill.md`.

## Alternative scartate

- **I backup S3 integrati di Coolify**: funzionano solo per i database creati come risorse separate di Coolify, non per un servizio dentro un Compose (ADR-005).
- **`rclone sync`**: per il motivo spiegato sopra.
- **Regole di ciclo di vita del bucket** per la conservazione: diverse per ogni provider, e fuori dal repository.
- **pgBackRest o l'archiviazione dei WAL**: permettono di tornare a un istante preciso, ma per un prodotto da 1 a 10 insegnanti un giorno di dati come perdita massima è accettabile, e la complessità non lo è.

## Conseguenze

- Si possono perdere fino a 24 ore di dati (RPO). Il ripristino misurato su 78.000 lezioni richiede 20 secondi (RTO del database, esclusi download e riavvio).
- Senza le password di cifratura, i backup off-site sono inutilizzabili. Il runbook lo ripete.
- Le copie remote hanno anche i link fisici giornaliero, settimanale e mensile come file separati: si occupa un po' più spazio, ma è tutto molto piccolo (1,8 MB per 78.000 lezioni).
- La configurazione di rclone non è stata provata contro un bucket vero: è il primo controllo dopo il deploy.

## Aggiornamento (2026-11-10)

Sul server di produzione i backup li gestisce chi lo amministra (ADR-026). Questi servizi sono passati nel file opzionale `docker-compose.backup.yml` e non fanno più parte del deploy su Coolify.
