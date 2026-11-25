# Runbook di produzione — MusicStudio

Questo documento dice cosa fare, passo per passo, per mettere in produzione MusicStudio su Coolify, tornare indietro se qualcosa va storto, cambiare un segreto e ripristinare il database. È scritto per essere seguito senza aiuto. Le decisioni dietro ogni passo sono negli ADR citati.

## Cosa c'è in produzione

Il file `docker-compose.coolify.yml` avvia sei servizi:

- `db`: PostgreSQL 16 (immagine fissata alla versione provata, `16.15`), con i dati in un volume. Per 16 contro 18 vedi `postgresql-16-vs-18.md`.
- `redis`: cache, contatori del rate limiting e coda di Celery.
- `backend`: l'API (gunicorn). È l'unico servizio con un dominio.
- `worker`: esegue i task Celery (promemoria, webhook Stripe).
- `beat`: lo scheduler che mette in coda i task periodici.
- `web`: il portale web (la SPA React), servito da nginx senza privilegi di amministratore (ADR-025).

I **backup del database non sono nel deploy**: li gestisce chi amministra il server, con i suoi strumenti (ADR-026). I servizi di backup dello stack, `backup` e `offsite`, sono nel file opzionale `docker-compose.backup.yml`, da usare solo su un server che non ha un suo sistema di backup.

Nessun servizio pubblica porte. Il proxy di Coolify (Traefik) riceve l'HTTPS e inoltra al `backend` e al `web`, ognuno con il suo dominio. Un test del backend (`config/tests/test_deploy_compose.py`) fallisce se qualcuno aggiunge una porta pubblicata o toglie un healthcheck.

## Staging

Prima del dominio definitivo si usa un **ambiente di staging**: una seconda risorsa su Coolify, dallo stesso repository e dallo stesso branch, con tutto separato.

- **Domini propri**, per esempio `https://app-staging.tuodominio.it:8080` per `web` e `https://api-staging.tuodominio.it:8000` per `backend`; `API_PUBLIC_URL` punta all'API di staging.
- **Database e segreti propri**: Coolify genera credenziali nuove per la nuova risorsa. Mai i dati veri della produzione.
- `SENTRY_ENVIRONMENT=staging`, così gli errori dello staging non si mescolano a quelli della produzione.
- `ROBOTS_TAG` **non impostata**: lo staging resta nascosto ai motori di ricerca.
- Stripe con chiavi di **test**, come sempre.
- Nessun dato di prova automatico: gli account si creano con la registrazione o con `create_teacher` (vedi "Partire con dati veri"). Il comando `seed_demo` non esiste più.

## Partire con dati veri

Dal terminale del container `backend`. La password non si passa mai sulla riga di comando (finirebbe nella cronologia della shell): il comando la chiede due volte, oppure la legge dalla variabile `ACCOUNT_PASSWORD` se è impostata. Deve superare i controlli di Django (almeno 8 caratteri, non troppo comune, non solo numeri).

1. Il primo titolare: `python manage.py create_teacher --email tu@dominio.it --studio-name "Il nome del tuo studio"`. Senza `--studio-name` crea un insegnante che lavora da solo. Se l'email esiste già il comando si ferma: non tocca mai la password di un account esistente.
2. Studenti, pacchetti e lezioni si inseriscono dall'app e dal portale web (pulsanti "Nuovo studente", "Nuovo pacchetto", "Programma lezione").
3. Un genitore (portale in sola lettura): serve l'id dello studente, che si legge nell'indirizzo della pagina dello studente (`/students/7`). Poi `python manage.py create_parent --email genitore@dominio.it --student-id 7`. Con più figli si ripete `--student-id`. Lo stesso comando su un genitore già esistente aggiunge solo i collegamenti.

Se un database ha ancora account di prova creati in passato dal vecchio `seed_demo` (`owner@example.com` e gli altri), vanno tolti prima di usarlo con persone vere: la via più pulita è azzerare i dati (vedi "Azzerare un database di prova").

Le verifiche dopo il deploy, la misura con `scripts/measure-resources.sh` e la checklist "go / no-go" si fanno qui, prima di pubblicare il dominio vero.

## Primo deploy

1. In Coolify crea una risorsa **Docker Compose** dal repository GitHub, branch `main`, file `docker-compose.coolify.yml`.
2. Sul servizio `backend` imposta il dominio con il suffisso della porta del container, per esempio `https://api.tuodominio.it:8000`. Il suffisso deve coincidere con `PORT`.
3. Le credenziali del database e le chiavi `DJANGO_SECRET_KEY` e `JWT_SIGNING_KEY` le genera Coolify da solo (variabili `SERVICE_PASSWORD_*`). Non vanno inventate.
4. Imposta le variabili obbligatorie. Coolify blocca il deploy finché mancano: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `DEFAULT_FROM_EMAIL`.
5. Imposta le variabili consigliate:
   - `SENTRY_DSN`: dal progetto Sentry (vedi "Sentry" più sotto). Se resta vuota, l'API funziona lo stesso.
   - `STRIPE_API_KEY` e `STRIPE_WEBHOOK_SECRET`: solo chiavi di **test** (`sk_test_`, `rk_test_`). Una chiave live blocca l'avvio, per scelta (ADR-013).
   - `STRIPE_WEBHOOK_ALLOWED_IPS`: la lista degli IP da cui Stripe invia i webhook, separati da virgola. Si prende da `https://stripe.com/files/ips/ips_webhooks.txt` (ADR-021).
6. Lascia `TRUSTED_PROXY_COUNT=1`: dietro Coolify c'è un solo proxy che aggiunge l'indirizzo del client. Se metti Cloudflare davanti a Coolify, diventa 2.
7. Per il portale web:
   - sul servizio `web` imposta il dominio con il suffisso della porta del container, per esempio `https://app.tuodominio.it:8080`;
   - imposta `API_PUBLIC_URL` con l'indirizzo pubblico delle API, senza percorso, per esempio `https://api.tuodominio.it`. Serve due volte: entra nella build del portale e nella Content-Security-Policy. Se manca o non inizia con `https://`, il container del portale non parte, apposta;
   - `CORS_ALLOWED_ORIGINS` del backend vale per default l'indirizzo del servizio `web`: le API accettano chiamate dal browser solo dal portale. Se il dominio del portale è diverso, impostalo a mano.
   - `FRONTEND_URL`: l'indirizzo pubblico del portale. Entra nei link delle email e, come `VITE_SITE_URL`, nella build: da lì vengono il link canonico, l'anteprima social, `robots.txt` e `sitemap.xml`. Senza, il portale funziona ma non ha sitemap. Cambiarla ricostruisce il portale.
   - `ROBOTS_TAG`: **non impostarla**. Il portale manda `noindex, nofollow`, quindi resta fuori dai motori di ricerca. Si imposta `index, follow` solo in produzione, quando i testi di privacy sono definitivi, e con un riavvio del servizio `web` (non serve ricostruirlo). Il backend manda sempre `noindex`.
8. Avvia il deploy. Al primo avvio il `backend` applica le migrazioni (`RUN_MIGRATIONS=1`).

## Azzerare un database di prova

Serve per togliere tutti i dati di prova (account, studi, studenti, lezioni, pagamenti, registro delle attività, inviti) da una risorsa che resta in piedi. **È irreversibile: mai su dati veri.**

1. Dal terminale del container `backend`: `python manage.py flush --noinput`. Svuota tutte le tabelle e mantiene lo schema, quindi non serve rifare le migrazioni.
2. Dal terminale del container `redis`: `redis-cli FLUSHALL`. Svuota le code di Celery, i contatori dei limiti di richieste e la cache.
3. Ricomincia con una registrazione nuova dal portale, o con `create_teacher` (vedi "Partire con dati veri").

Dopo l'azzeramento si può cambiare `FIELD_ENCRYPTION_KEYS` senza perdere niente: non esistono più note cifrate con la chiave vecchia. La strada alternativa, più drastica, è eliminare i volumi `db-data` e `redis-data` della risorsa e ridistribuire: serve quando si vuole anche una password del database nuova.

## Verifiche dopo ogni deploy

1. `https://api.tuodominio.it/health/live/` risponde `{"status": "ok"}`.
2. `https://api.tuodominio.it/health/ready/` risponde 200 con `database` e `redis` a `ok`. Se risponde 503, i log del `backend` dicono quale controllo è fallito.
3. Una richiesta con `curl -i` mostra l'header `X-Request-ID`. Con quel valore trovi la riga di log della richiesta.
4. Dal terminale del container `backend` in Coolify: `python manage.py raise_test_error`. L'errore deve comparire in Sentry entro un minuto, senza token né email.
5. In Coolify tutti i servizi devono risultare "healthy". Il `worker` impiega fino a un minuto.
6. Apri il portale, fai login e ricarica una pagina interna, per esempio `/students`: deve riapparire il portale, non un errore 404. Negli strumenti per sviluppatori del browser, la risposta della pagina deve avere l'intestazione `Content-Security-Policy`.
7. `curl -I` sul portale mostra `content-security-policy`, `strict-transport-security` e `x-robots-tag: noindex, nofollow` (o `index, follow` se l'hai aperto). `curl -I` sul backend mostra `x-robots-tag: noindex, nofollow`.
8. `/robots.txt` è un file di testo con `Allow: /` e, se `FRONTEND_URL` è impostata, la riga `Sitemap:`; `/sitemap.xml` elenca solo `/` e `/register`. Se `/robots.txt` risponde con una pagina HTML, il fallback del portale sta rispondendo al posto del file.
9. Nessuna porta delle nostre app è pubblicata: dall'esterno le porte 8080 e 8000 risultano chiuse, e in `docker ps` non c'è `0.0.0.0` davanti.
10. Nel log del `backend`, dopo l'avvio, non compare nessuna riga di errore (in particolare niente `Control server error`).

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

## Account bloccato o senza secondo fattore

Due comandi per l'operatore, dal terminale del `backend`. Entrambi scrivono nell'audit log (`account.unlock_by_operator`, `mfa.reset_by_operator`).

- **Account bloccato** dopo cinque password sbagliate (si sblocca da solo dopo 15 minuti, poi 30, 60... fino a 24 ore): `python manage.py unlock_account email@esempio.it`. Azzera anche il livello del blocco.
- **Telefono e codici di recupero persi**: `python manage.py reset_mfa email@esempio.it`. Dopo il comando basta la password per entrare, quindi **verifica prima chi sei davvero** (per esempio una chiamata o un messaggio da un canale che già conosci). Poi chiedi alla persona di riattivare la verifica in due passaggi.
- Chi dimentica la password non ha bisogno di questi comandi: il reset via email toglie anche il blocco.

## Admin solo per operatori (fase 10)

Dalla fase 10 l'admin (`DJANGO_ADMIN_URL`) lo apre solo un **operatore**: un account attivo, staff e senza ruolo di studio, come quelli creati con `createsuperuser`. Tutti gli altri ricevono 404. In produzione il login chiede anche il **codice TOTP** (`ADMIN_REQUIRE_TOTP`, vero per default). Dettagli in ADR-041.

**Prima del deploy della fase 10**, l'operatore attiva il TOTP, altrimenti resta fuori dall'admin:

1. Un account creato con `createsuperuser` ha l'email **non confermata**, e l'API rifiuta il login finché non lo è. Chiedi il link con `POST /api/v1/auth/confirm-email/resend/` (`{"email": "..."}`) e aprilo dalla posta.
2. Accedi all'API con l'account operatore (`POST /api/v1/auth/token/`, email e password) e prendi il token di accesso.
3. `POST /api/v1/auth/mfa/setup/` restituisce l'URI `otpauth://`: aprilo con l'app di autenticazione (o trasformalo in QR).
4. `POST /api/v1/auth/mfa/confirm/` con il primo codice. La risposta contiene **dieci codici di recupero**: conservali fuori dal server.

Se il deploy è già avvenuto senza TOTP attivo: imposta `ADMIN_REQUIRE_TOTP=false` nelle variabili di Coolify, rideploya, attiva il TOTP come sopra, poi **togli la variabile** e rideploya. Per limitare l'admin a certi indirizzi, metti `ADMIN_ALLOWED_IPS` (lista separata da virgole); vuota vuol dire nessun limite.

Nell'admin i pagamenti, le ricevute, i consensi, il registro, le lezioni, i pacchetti e gli studenti sono in sola lettura. Si modificano solo gli utenti, e ogni modifica finisce nel registro (`admin.change`). Un operatore che perde telefono e codici: `python manage.py reset_mfa email@esempio.it` (vedi sopra).

## Sentry

1. Crea un account gratuito su sentry.io e un progetto di tipo **Django**.
2. Copia il DSN nella variabile `SENTRY_DSN` e fai redeploy.
3. Lascia `SENTRY_TRACES_SAMPLE_RATE=0`: le tracce di performance consumano in fretta la quota gratuita. Gli errori vengono inviati comunque.
4. In Sentry imposta un avviso via email per i nuovi errori.

## Backup

Su Coolify i backup li fa chi amministra il server (ADR-026). Da concordare con lui, una volta:

1. **Cosa salva.** Serve una copia **coerente** del database: un `pg_dump` (o `pg_dumpall`), oppure uno snapshot del disco fatto in modo atomico. Copiare i file del volume `db-data` mentre PostgreSQL è acceso **non** basta: la copia può essere inutilizzabile.
2. **Dove e quanto a lungo.** Fuori dal server, cifrata, con una conservazione di almeno 7 giorni.
3. **La prova.** Un dump in formato SQL si prova con `scripts/restore-drill.sh <file>`, che lo ripristina in un database nuovo e confronta le righe. Registra la prova in `restore-drill.md`, in questa cartella.

## Backup con i servizi dello stack (opzionale)

Solo su un server **senza** un suo sistema di backup: `docker compose -f docker-compose.coolify.yml -f docker-compose.backup.yml up -d`. Poi:

1. Crea un bucket su un servizio S3-compatibile che **non** sia AWS: per esempio Backblaze B2, Cloudflare R2 o Hetzner Object Storage. Crea una chiave di accesso limitata a quel bucket.
2. Imposta `RCLONE_S3_ENDPOINT`, `RCLONE_S3_ACCESS_KEY_ID`, `RCLONE_S3_SECRET_ACCESS_KEY` e `RCLONE_BUCKET`.
3. Genera le due password di cifratura sul tuo computer con `rclone obscure "$(openssl rand -base64 32)"`, due volte. Mettile in `RCLONE_CRYPT_PASSWORD` e `RCLONE_CRYPT_PASSWORD2`. **Salvale anche in un password manager**: senza, i backup sono illeggibili.
4. Facoltativo ma consigliato: crea un controllo su healthchecks.io con periodo di un giorno e metti l'URL in `BACKUP_ALERT_URL`. Se un giorno il backup non arriva, ricevi un'email.
5. Dopo il primo giorno, controlla nel bucket che esistano i file. I nomi sono cifrati: è normale.

## Ripristino del database

La procedura è nello script `scripts/restore-drill.sh` e la prova eseguita è registrata in `restore-drill.md`, in questa cartella.

1. Ferma `backend`, `worker` e `beat` in Coolify, così nessuno scrive durante il ripristino.
2. Prendi il dump dal sistema di backup di chi amministra il server. Con i servizi dello stack, invece: dal volume `db-backups`, oppure dal bucket con `scripts/restore-drill.sh --from-remote daily/<file>`.
3. Ripristina in un database **nuovo** e controlla i conteggi delle righe con lo script. Solo quando i conteggi tornano, punta l'applicazione al database ripristinato.
4. Riavvia i servizi e fai le verifiche dopo il deploy.

## Pagamenti online sul conto dello studio (fase 9, spenti)

La funzione è costruita ma **spenta**: finché `ONLINE_PAYMENTS_ENABLED` non è `true`, le rotte `/payment-account/` rispondono 404, nessun pacchetto è pagabile online e il portale non mostra nulla. Restano in **modalità test**: una chiave `sk_live_` blocca ancora l'avvio. Per i soldi veri servono un emendamento alla costituzione, i termini d'uso e una decisione scritta del titolare: non fanno parte di questo capitolo. Il perché è in ADR-037.

**Variabili** (nel Compose, già previste):

- `ONLINE_PAYMENTS_ENABLED`: `false` di default. `true` solo per provare.
- `STRIPE_CONNECT_WEBHOOK_SECRET`: il segreto dell'endpoint dei conti collegati (sotto).
- `THROTTLE_PAYMENT_ACCOUNT`: limite di frequenza di onboarding e rilettura (default `20/hour`).
- `CHECKOUT_SUCCESS_URL` e `CHECKOUT_CANCEL_URL`: dove Stripe rimanda chi ha pagato. Valori: `https://<portale>/payments/success` e `https://<portale>/payments/cancel`.

**Registrare l'endpoint dei conti collegati su Stripe** (nel sandbox o, più avanti, in produzione):

1. Nella Dashboard di Stripe: Sviluppatori, Webhook, aggiungi un endpoint. Come ascoltatore scegli **"Account connessi"** (non "Il tuo account").
2. Indirizzo: `https://<backend>/api/v1/webhooks/stripe-connect/`.
3. Eventi da selezionare: `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired`, `refund.created`, `refund.updated`, `charge.dispute.created`, `charge.dispute.closed`, `account.application.deauthorized`.
4. Copia il segreto di firma (`whsec_...`) in `STRIPE_CONNECT_WEBHOOK_SECRET` e fai redeploy. Non incollarlo in chat né nel repository.
5. Se usi `STRIPE_WEBHOOK_ALLOWED_IPS`, vale anche per questo endpoint.

In locale, con la Stripe CLI: `stripe listen --forward-connect-to localhost:8000/api/v1/webhooks/stripe-connect/` stampa il segreto da usare.

**Cosa guardare quando qualcosa non torna**

- Nella pagina "Come pagare" il titolare vede lo **stato del conto** e, sotto "Da controllare su Stripe", gli ultimi eventi che non combaciano col registro (un rimborso senza pagamento, un importo diverso, un doppio pagamento, una valuta diversa): tipo e importo, mai i dati di chi ha pagato.
- Un conto **limitato** da Stripe smette di offrire il pagamento online. Il titolare apre la sua pagina Stripe e segue ciò che chiede. Lo stato si aggiorna da solo ogni ora, o subito con "Controlla lo stato".
- Un conto **scollegato** (il titolare ha tolto MusicStudio dal suo Stripe) si riparte con "Ricomincia".
- Gli eventi già elaborati si cancellano dopo 90 giorni (ogni notte).

**Ancora da verificare con Stripe vero** (serve un conto di prova che finisca l'attivazione sulla sua pagina, con l'SMS di test `000-000`): un pagamento diretto, un rimborso, una contestazione, la forma degli eventi e se PayPal compare.

## Cose che restano da fare a mano

- Il deploy di produzione e la misura del tempo di rollback (lo staging è stato fatto il 13 novembre 2026).
- L'account Sentry e il DSN.
- La prova di ripristino da un backup vero di chi amministra il server.
- La protezione del branch su GitHub, così la CI rossa blocca il merge.
- Fase 9: la prova completa sul sandbox di Stripe, l'endpoint webhook dei conti collegati, i termini d'uso e, solo se e quando si deciderà, i soldi veri.
