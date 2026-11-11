# Deploy di staging, passo per passo (versione di oggi)

Stato: 11 novembre 2026, branch `staging/backend`, CI verde su PostgreSQL 16.15 e 18.6. Questa guida
mette online backend e portale **senza aspettare la prova dell'SMTP** (che si fa dopo). Per i dettagli
e le motivazioni: `docs/operations/runbook.md`. I valori segreti si incollano **solo** nelle variabili di
Coolify, mai nel repository né in chat.

Nomi usati qui (cambiali se i tuoi sono diversi, ma poi cambiali **ovunque**, app mobile compresa):

- API: `https://stagingapimusic.christianseminerio.dev`
- Portale: `https://app-staging.christianseminerio.dev`

L'APK di staging è già puntato sull'API `stagingapimusic.christianseminerio.dev`.

## 1. DNS (prima di tutto: impiega tempo)

Dal registrar, due record **A** verso l'indirizzo IP del server Coolify (te lo dà Elio):

| Nome | Tipo | Valore |
|---|---|---|
| `stagingapimusic` | A | IP del server |
| `app-staging` | A | IP del server |

Controllo, anche dopo qualche minuto: `dig +short stagingapimusic.christianseminerio.dev` deve stampare l'IP.
Non serve aspettare per il passo 2: Coolify può preparare tutto mentre il DNS si propaga.

## 2. Risorsa in Coolify

1. Nuova risorsa, tipo **Docker Compose**, dal repository GitHub `aZaChris/MusicStudio`.
2. Branch: `staging/backend`. File Compose: `docker-compose.coolify.yml`. Base directory: `/`.
3. Domini (il numero dopo i due punti è la porta del container e **deve esserci**):
   - servizio `backend`: `https://stagingapimusic.christianseminerio.dev:8000`
   - servizio `web`: `https://app-staging.christianseminerio.dev:8080`
4. Gli altri servizi (`db`, `redis`, `worker`, `beat`) **non** hanno dominio.
5. Le password del database e le chiavi `DJANGO_SECRET_KEY` e `JWT_SIGNING_KEY` le genera Coolify da solo:
   non inventarle e non toccarle.

## 3. Variabili d'ambiente

Coolify blocca il deploy finché mancano quelle **obbligatorie**.

| Variabile | Valore | Note |
|---|---|---|
| `API_PUBLIC_URL` | `https://stagingapimusic.christianseminerio.dev` | Obbligatoria. Senza barra finale e senza percorso. Deve iniziare con `https://`. |
| `FIELD_ENCRYPTION_KEYS` | la chiave dal gestore di password | Obbligatoria. **Se la perdi, perdi le note.** Una sola chiave per ora. |
| `SMTP_HOST` | `smtp.gmail.com` (o il tuo provider) | Obbligatoria. |
| `SMTP_USER` | il tuo indirizzo Gmail (o l'utente del provider) | Obbligatoria. |
| `SMTP_PASSWORD` | la password per app di Gmail | Obbligatoria. Se non ce l'hai ancora, vedi sotto. |
| `DEFAULT_FROM_EMAIL` | lo stesso indirizzo Gmail | Obbligatoria. Con Gmail deve coincidere con l'utente. |
| `SENTRY_ENVIRONMENT` | `staging` | Consigliata. |
| `SENTRY_DSN` | il DSN del progetto Sentry | Facoltativa. Lasciala vuota se non hai fatto Sentry. |
| `FRONTEND_URL` | `https://app-staging.christianseminerio.dev` | Consigliata (default dal dominio del servizio `web`). I link nelle email partono da qui. |
| `TRUSTED_PROXY_COUNT` | `1` | Già il default. Non toccare. |
| `ANDROID_APK_URL` | il link alla build Android (vedi sotto) | Facoltativa. Se è vuota, la vetrina dice "la versione per Android arriva a breve". Cambiarla **ricostruisce** il portale. |

**Se oggi non hai ancora la password per app di Gmail:** metti comunque `SMTP_HOST=smtp.gmail.com`, il tuo
indirizzo in `SMTP_USER` e `DEFAULT_FROM_EMAIL`, e un segnaposto in `SMTP_PASSWORD` (per esempio
`da-impostare`). Il deploy parte. Registrazione, invito e reset **non** manderanno email finché non
metti la password vera e fai redeploy. Il resto funziona.

**Link per scaricare l'app (facoltativo):** apri la build Android su expo.dev (progetto `musicstudio-app`, scheda
Builds), copia il link di installazione e mettilo in `ANDROID_APK_URL`. Prima di fidarti, aprilo **in una finestra
anonima** del browser: deve scaricare o mostrare la pagina di installazione senza chiederti di accedere a Expo.
Deve iniziare con `https://`. Ricorda che l'APK attuale è puntato sull'API di staging.

**Stripe: lascialo vuoto oggi** (`STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`,
`STRIPE_WEBHOOK_ALLOWED_IPS`). Il pagamento online risponde "non disponibile" (503) e tutto il resto
funziona. Si configura dopo (`docs/CHECKLIST_17.md`, passi 3 e 5).

## 4. Deploy

1. Avvia il deploy. Il primo build del backend e del portale impiega qualche minuto.
2. Al primo avvio il backend applica da solo le migrazioni.
3. Aspetta che tutti i servizi risultino **healthy** (il `worker` impiega fino a un minuto).

## 5. Verifiche (con il DNS già propagato)

1. `https://stagingapimusic.christianseminerio.dev/health/live/` risponde `{"status": "ok"}`.
2. `https://stagingapimusic.christianseminerio.dev/health/ready/` risponde 200 con `database` e `redis` a `ok`.
3. `https://app-staging.christianseminerio.dev` mostra la pagina di accesso del portale.
4. Ricarica una pagina interna del portale (per esempio `/students`): deve riapparire il portale, non un 404.

## 6. Il primo account senza email

Dal terminale del servizio `backend` in Coolify (la password la chiede il comando, due volte):

1. Il titolare: `python manage.py create_teacher --email tuoindirizzo+titolare@gmail.com --studio-name "Nome dello studio"`
   (l'account nasce già con l'email confermata, quindi puoi accedere subito).
2. Accedi dal portale. Da lì crea studenti, pacchetti e lezioni.
3. Un genitore, **senza email**: leggi l'id dello studente nell'indirizzo della sua pagina (`/students/7`), poi
   `python manage.py create_parent --email tuoindirizzo+genitore@gmail.com --student-id 7`.
4. **Non** lanciare `seed_demo`: crea account con una password nota.

Con gli alias con il più (`tuoindirizzo+ruolo@gmail.com`) ogni ruolo è una persona diversa per l'app e tutte
le email arrivano nella tua casella.

## 7. Cosa non funziona finché non provi l'SMTP

Registrazione di un nuovo studio, conferma dell'email, "password dimenticata", inviti (insegnanti, genitori,
studenti adulti). Si provano **dopo** il test dell'SMTP (`docs/TODO_PROPRIETARIO.md`, punto 6), che puoi fare
anche dal tuo computer prima di toccare Coolify. Quando l'SMTP funziona: aggiorna `SMTP_PASSWORD` (se era un
segnaposto), fai redeploy, e rifai il giro con gli alias.

## 8. Se qualcosa va storto

| Sintomo | Dove guardare |
|---|---|
| La build del backend si ferma con `ImproperlyConfigured` | Log di build. Scrivimi la riga con il nome della variabile. |
| Coolify non fa partire il deploy | Manca una variabile obbligatoria: la schermata dice quale. |
| `health/ready` risponde 503 | Log del `backend`: dice se è il database o Redis. |
| Il portale si apre ma il login dà un errore di rete | `API_PUBLIC_URL` sbagliata (si cambia **ricostruendo** il portale) o `CORS_ALLOWED_ORIGINS` diverso dal dominio del portale. |
| Il container `web` non parte | `API_PUBLIC_URL` manca o non inizia con `https://`. |
| Il `worker` o il `beat` non diventano healthy | I loro log: di solito una variabile mancante (`FIELD_ENCRYPTION_KEYS`, `SMTP_*`). |
| Un deploy nuovo va peggio del precedente | Rollback: runbook, sezione "Rollback" (Redeploy del deploy precedente). |

Incollami l'errore **senza password né chiavi** e lo sistemo.

## 9. Dopo il deploy

- Cambia in GitHub la protezione dei branch (`docs/CHECKLIST_17.md`, passo 8): i controlli adesso si chiamano
  `backend (postgres 16.15)` e `backend (postgres 18.6)`, oltre a `frontend`, `web-image`, `secrets` e la CI mobile.
- Dopo il primo accesso, controlla anche lo spazio e la memoria con `scripts/measure-resources.sh`
  (runbook), perché il server è condiviso con altri servizi di Elio.
