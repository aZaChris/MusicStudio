# Checklist delle 17:00: account, chiavi e deploy di staging

Da eseguire in ordine. Ogni passo dice dove andare, cosa fare e cosa annotare. I valori segreti
**non** vanno mai nel repository né in chat: si incollano solo nelle variabili d'ambiente di Coolify.
Al posto di `tuodominio.it` metti il tuo dominio. Contesto e motivazioni sono in `docs/TASKS_SPLIT.md`.

Tempo stimato: da un'ora e mezza a due ore, quasi tutto in attesa del DNS.

## 0. Database su questo PC (2 minuti, anche subito)

Senza questo i test del backend non partono su questo computer.

1. Nel terminale WSL: `sudo -u postgres createuser --createdb christian`
2. Poi: `sudo -u postgres createdb -O christian musicstudio`
   (se dice "already exists", va bene lo stesso).
3. Controllo: `psql -d musicstudio -c "select 1"` deve rispondere `1`.
4. Dimmi "fatto": lancio io tutta la suite e i test di `create_teacher` e `create_parent`.

## 1. DNS (prima di tutto, perché impiega tempo a propagarsi)

1. Chiedi al tuo amico l'indirizzo IP del server Coolify.
2. Nel pannello del registrar, aggiungi due record **A**:
   - `api-staging` verso l'IP del server;
   - `app-staging` verso l'IP del server.
3. Controllo (anche dopo qualche minuto): `dig +short api-staging.tuodominio.it` deve stampare l'IP.

## 2. Email (SMTP)

1. Crea un account su un provider con server nell'UE, per esempio Brevo (piano gratuito).
2. Aggiungi il dominio mittente nel provider. Il provider ti dà dei record DNS: copiali nel
   registrar (SPF, DKIM e, se proposto, DMARC).
3. Attendi che il provider segni il dominio come **verificato**.
4. Prendi le credenziali **SMTP** (non la chiave API): host, porta 587, utente, password.
5. Annota, senza la password: `SMTP_HOST`, `SMTP_USER`, e `DEFAULT_FROM_EMAIL` (per esempio
   `noreply@tuodominio.it`).

## 3. Stripe (solo modalità test)

1. Accedi a dashboard.stripe.com. Dal selettore dell'account in alto, crea una **sandbox** dedicata
   chiamata `MusicStudio staging`.
2. Nella sandbox: Developers, API keys, **Create restricted key**. Nome `musicstudio-staging`.
   Permesso: **Checkout Sessions: Write**. Tutto il resto: None.
3. Copia la chiave: inizia con `rk_test_`. Se inizia con `rk_live_` o `sk_live_` hai sbagliato
   ambiente, e l'API si rifiuterebbe di partire.
4. **Il webhook si configura al passo 5**, dopo il deploy, perché serve l'indirizzo pubblico.
5. Apri `https://stripe.com/files/ips/ips_webhooks.txt` e prepara gli IP su una riga, separati da
   virgola: è il valore di `STRIPE_WEBHOOK_ALLOWED_IPS`.

## 4. Deploy di staging su Coolify

Segui `docs/operations/runbook.md`, sezioni "Staging" e "Primo deploy". In breve:

1. Nuova risorsa **Docker Compose** dal repository GitHub, branch `staging/backend`, file
   `docker-compose.coolify.yml`.
2. Dominio del servizio `backend`: `https://api-staging.tuodominio.it:8000`.
3. Dominio del servizio `web`: `https://app-staging.tuodominio.it:8080`.
4. Variabili da impostare (le chiavi Django e JWT e la password del database le genera Coolify, non
   inventarle):
   - `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `DEFAULT_FROM_EMAIL` (passo 2)
   - `STRIPE_API_KEY` = la `rk_test_` del passo 3
   - `STRIPE_WEBHOOK_ALLOWED_IPS` = la lista del passo 3
   - `API_PUBLIC_URL=https://api-staging.tuodominio.it`
   - `CHECKOUT_SUCCESS_URL=https://app-staging.tuodominio.it/payments/success`
   - `CHECKOUT_CANCEL_URL=https://app-staging.tuodominio.it/payments/cancel`
   - `TRUSTED_PROXY_COUNT=1`
   - `SENTRY_ENVIRONMENT=staging` (e `SENTRY_DSN` se fai il passo 7)
5. Lancia il deploy. Il primo build impiega qualche minuto.
6. Verifiche (runbook, "Verifiche dopo ogni deploy"):
   - `https://api-staging.tuodominio.it/health/live/` risponde `{"status": "ok"}`;
   - `https://api-staging.tuodominio.it/health/ready/` risponde 200;
   - in Coolify tutti i servizi sono "healthy";
   - il portale `https://app-staging.tuodominio.it` si apre.

## 5. Webhook di Stripe

1. Nella sandbox Stripe: Developers, Webhooks, **Add endpoint**.
2. URL: `https://api-staging.tuodominio.it/api/v1/webhooks/stripe/` (con la barra finale).
3. Eventi, solo questi quattro:
   - `checkout.session.completed`
   - `checkout.session.async_payment_succeeded`
   - `checkout.session.async_payment_failed`
   - `checkout.session.expired`
4. Copia il **Signing secret** (`whsec_...`) in `STRIPE_WEBHOOK_SECRET` su Coolify e fai redeploy.
5. Prova: nel portale paga un pacchetto con la carta di test `4242 4242 4242 4242`, una data futura
   e un CVC qualsiasi. Il pagamento deve comparire come registrato. In Stripe, nella pagina
   dell'endpoint, l'evento deve risultare consegnato con risposta 200.

## 6. Primo account vero in staging

Dal terminale del container `backend` in Coolify:

1. `python manage.py create_teacher --email tua@email.it --studio-name "Nome dello studio"`
   (la password te la chiede due volte).
2. Fai login nel portale con quell'account.
3. Non lanciare `seed_demo` se in staging userai dati di persone vere.

## 7. Sentry (facoltativo, 5 minuti)

1. sentry.io, account gratuito, nuovo progetto **Django**.
2. Copia il DSN in `SENTRY_DSN` su Coolify, redeploy.
3. Dal terminale del `backend`: `python manage.py raise_test_error`. L'errore deve comparire in
   Sentry entro un minuto.

## 8. Protezione dei branch su GitHub

1. GitHub, repository MusicStudio, Settings, Rules, **New branch ruleset**.
2. Target: `staging/backend` e `staging/mobile`.
3. Attiva "Require status checks to pass" e aggiungi `backend`, `frontend`, `web-image` e il job
   della CI mobile.
4. Attiva "Block force pushes".

## Alla fine, scrivimi

- "DB fatto" (passo 0), se non l'hai già detto.
- Gli indirizzi di staging (non i segreti).
- Quali passi sono andati e quali no, con il messaggio d'errore esatto.

Io aggiorno i task T017 e T018 e il runbook con quello che è successo davvero.
