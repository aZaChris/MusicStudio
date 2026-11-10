# Runbook di produzione — MusicStudio

Questo documento dice cosa fare, passo per passo, per mettere in produzione MusicStudio su Coolify, tornare indietro se qualcosa va storto, cambiare un segreto e ripristinare il database. È scritto per essere seguito senza aiuto. Le decisioni dietro ogni passo sono negli ADR citati.

## Cosa c'è in produzione

Il file `docker-compose.coolify.yml` avvia sette servizi:

- `db`: PostgreSQL 16, con i dati in un volume.
- `redis`: cache, contatori del rate limiting e coda di Celery.
- `backend`: l'API (gunicorn). È l'unico servizio con un dominio.
- `worker`: esegue i task Celery (promemoria, webhook Stripe).
- `beat`: lo scheduler che mette in coda i task periodici.
- `backup`: un `pg_dump` giornaliero con rotazione (ADR-005).
- `offsite`: copia i dump, cifrati, su un bucket fuori dal server (ADR-020).
- `web`: il portale web (la SPA React), servito da nginx senza privilegi di amministratore (ADR-025).

Nessun servizio pubblica porte. Il proxy di Coolify (Traefik) riceve l'HTTPS e inoltra al `backend` e al `web`, ognuno con il suo dominio. Un test del backend (`config/tests/test_deploy_compose.py`) fallisce se qualcuno aggiunge una porta pubblicata o toglie un healthcheck.

## Primo deploy

1. In Coolify crea una risorsa **Docker Compose** dal repository GitHub, branch `refactor/production-standards`, file `docker-compose.coolify.yml`.
2. Sul servizio `backend` imposta il dominio con il suffisso della porta del container, per esempio `https://api.tuodominio.it:8000`. Il suffisso deve coincidere con `PORT`.
3. Le credenziali del database e le chiavi `DJANGO_SECRET_KEY` e `JWT_SIGNING_KEY` le genera Coolify da solo (variabili `SERVICE_PASSWORD_*`). Non vanno inventate.
4. Imposta le variabili obbligatorie. Coolify blocca il deploy finché mancano: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `DEFAULT_FROM_EMAIL`.
5. Imposta le variabili consigliate:
   - `SENTRY_DSN`: dal progetto Sentry (vedi "Sentry" più sotto). Se resta vuota, l'API funziona lo stesso.
   - `STRIPE_API_KEY` e `STRIPE_WEBHOOK_SECRET`: solo chiavi di **test** (`sk_test_`, `rk_test_`). Una chiave live blocca l'avvio, per scelta (ADR-013).
   - `STRIPE_WEBHOOK_ALLOWED_IPS`: la lista degli IP da cui Stripe invia i webhook, separati da virgola. Si prende da `https://stripe.com/files/ips/ips_webhooks.txt` (ADR-021).
   - Le variabili `RCLONE_*` per il backup off-site (vedi "Backup off-site").
6. Lascia `TRUSTED_PROXY_COUNT=1`: dietro Coolify c'è un solo proxy che aggiunge l'indirizzo del client. Se metti Cloudflare davanti a Coolify, diventa 2.
7. Per il portale web:
   - sul servizio `web` imposta il dominio con il suffisso della porta del container, per esempio `https://app.tuodominio.it:8080`;
   - imposta `API_PUBLIC_URL` con l'indirizzo pubblico delle API, senza percorso, per esempio `https://api.tuodominio.it`. Serve due volte: entra nella build del portale e nella Content-Security-Policy. Se manca o non inizia con `https://`, il container del portale non parte, apposta;
   - `CORS_ALLOWED_ORIGINS` del backend vale per default l'indirizzo del servizio `web`: le API accettano chiamate dal browser solo dal portale. Se il dominio del portale è diverso, impostalo a mano.
8. Avvia il deploy. Al primo avvio il `backend` applica le migrazioni (`RUN_MIGRATIONS=1`).

## Verifiche dopo ogni deploy

1. `https://api.tuodominio.it/health/live/` risponde `{"status": "ok"}`.
2. `https://api.tuodominio.it/health/ready/` risponde 200 con `database` e `redis` a `ok`. Se risponde 503, i log del `backend` dicono quale controllo è fallito.
3. Una richiesta con `curl -i` mostra l'header `X-Request-ID`. Con quel valore trovi la riga di log della richiesta.
4. Dal terminale del container `backend` in Coolify: `python manage.py raise_test_error`. L'errore deve comparire in Sentry entro un minuto, senza token né email.
5. In Coolify tutti i servizi devono risultare "healthy". Il `worker` impiega fino a un minuto.
6. Apri il portale, fai login e ricarica una pagina interna, per esempio `/students`: deve riapparire il portale, non un errore 404. Negli strumenti per sviluppatori del browser, la risposta della pagina deve avere l'intestazione `Content-Security-Policy`.

## Rollback

1. In Coolify apri la risorsa, sezione **Deployments**, scegli il deploy precedente che funzionava e fai **Redeploy**. Coolify ricostruisce l'immagine da quel commit.
2. Le migrazioni non tornano indietro da sole. Per questo una release non deve mai cancellare o rinominare una colonna che la release precedente usa ancora: prima si smette di usarla, e solo nella release successiva la si rimuove. Se una migrazione va annullata davvero, si usa `python manage.py migrate <app> <migrazione_precedente>` dal terminale del container, **prima** del redeploy.
3. Il rollback è riuscito quando le verifiche dopo il deploy passano di nuovo. Il tempo da misurare la prima volta è quello tra il click su Redeploy e `/health/ready/` a 200.

## Cambiare un segreto

- **`JWT_SIGNING_KEY`**: cambiarla invalida **tutti** i token di tutti gli utenti. Tutti dovranno fare di nuovo il login. È il "pulsante rosso" se la chiave è stata esposta.
- **Le sessioni di un solo account** (telefono rubato): dal terminale del `backend`, `python manage.py revoke_sessions email@esempio.it`. Oppure, dall'admin, l'azione "Revoke all sessions" sugli utenti selezionati. Il token di accesso già emesso funziona ancora per al massimo 15 minuti (ADR-018).
- **`DJANGO_SECRET_KEY`**: invalida le sessioni dell'admin e i link firmati. Non tocca i JWT, che hanno la loro chiave.
- **Chiavi Stripe**: si ruotano nella Dashboard di Stripe in test mode, poi si aggiorna la variabile e si fa redeploy. Anche il segreto del webhook va aggiornato insieme all'endpoint.
- **Password di cifratura dei backup** (`RCLONE_CRYPT_PASSWORD*`): **non cambiarle**. I backup già caricati restano leggibili solo con le password vecchie. Se proprio devi, crea un nuovo percorso nel bucket e conserva le vecchie password finché i vecchi backup non scadono.

Dopo ogni cambio: redeploy e verifiche.

## Sentry

1. Crea un account gratuito su sentry.io e un progetto di tipo **Django**.
2. Copia il DSN nella variabile `SENTRY_DSN` e fai redeploy.
3. Lascia `SENTRY_TRACES_SAMPLE_RATE=0`: le tracce di performance consumano in fretta la quota gratuita. Gli errori vengono inviati comunque.
4. In Sentry imposta un avviso via email per i nuovi errori.

## Backup off-site

1. Crea un bucket su un servizio S3-compatibile che **non** sia AWS: per esempio Backblaze B2, Cloudflare R2 o Hetzner Object Storage. Crea una chiave di accesso limitata a quel bucket.
2. Imposta `RCLONE_S3_ENDPOINT`, `RCLONE_S3_ACCESS_KEY_ID`, `RCLONE_S3_SECRET_ACCESS_KEY` e `RCLONE_BUCKET`.
3. Genera le due password di cifratura sul tuo computer con `rclone obscure "$(openssl rand -base64 32)"`, due volte. Mettile in `RCLONE_CRYPT_PASSWORD` e `RCLONE_CRYPT_PASSWORD2`. **Salvale anche in un password manager**: senza, i backup sono illeggibili.
4. Facoltativo ma consigliato: crea un controllo su healthchecks.io con periodo di un giorno e metti l'URL in `BACKUP_ALERT_URL`. Se un giorno il backup non arriva, ricevi un'email.
5. Dopo il primo giorno, controlla nel bucket che esistano i file. I nomi sono cifrati: è normale.

## Ripristino del database

La procedura è nello script `scripts/restore-drill.sh` e la prova eseguita è registrata in `restore-drill.md`, in questa cartella.

1. Ferma `backend`, `worker` e `beat` in Coolify, così nessuno scrive durante il ripristino.
2. Prendi il dump: quello locale nel volume `db-backups`, oppure quello off-site con `scripts/restore-drill.sh --from-remote daily/<file>` da una macchina che ha rclone configurato.
3. Ripristina in un database **nuovo** e controlla i conteggi delle righe con lo script. Solo quando i conteggi tornano, punta l'applicazione al database ripristinato.
4. Riavvia i servizi e fai le verifiche dopo il deploy.

## Cose che restano da fare a mano

- Il primo deploy reale e la misura del tempo di rollback.
- L'account Sentry e il DSN.
- Il bucket, le credenziali e la prova di ripristino dal bucket vero.
- La protezione del branch su GitHub, così la CI rossa blocca il merge.
