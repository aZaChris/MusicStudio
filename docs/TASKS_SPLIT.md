# Divisione dei task: cosa fa Claude, cosa fa Christian

Data: 11 novembre 2026. Branch: `main` (backend + portale web) e `mobile` (app).
Stack di riferimento: quello del repository (Django + DRF, PostgreSQL 16, Redis, Celery, React + Vite,
Expo, deploy su **Coolify**). AWS è fuori perimetro (constitution: "No AWS").

## Stato di partenza (Step 0)

**Già reale, nessun mock.** Il portale web e l'app chiamano le API vere. Login JWT con refresh ruotato
e logout con lista nera; ruoli titolare, insegnante e genitore; studi con isolamento tra tenant;
studenti, pacchetti, lezioni (con conflitti di orario bloccati dal database) e pagamenti manuali.
Pagamento online con Stripe Checkout in modalità test, dietro `apps/payments/gateway.py`, con webhook
firmato e idempotente. Promemoria via email con outbox. Comandi `create_teacher` e `create_parent`
per creare account veri.

**Manca (da costruire).** Registrazione self-service, reset password, verifica email, MFA, account
allievo, ricorrenze delle lezioni, progressi, note e materiale, consenso del genitore, esportazione e
cancellazione GDPR, audit log, cifratura dei campi sensibili.

**Rotto su questo PC.** Solo l'ambiente: PostgreSQL non accetta l'utente dei test (vedi B0).
Web: 56 test verdi, TypeScript pulito. Mobile: 63 test verdi, TypeScript pulito. Backend: 46 test
verdi e 207 in errore per la connessione al database. I test di `create_teacher` e `create_parent`
scritti ieri **non sono mai stati eseguiti**: vanno eseguiti appena il DB funziona.

## A) Cosa posso fare da solo

Piano: fase spec-kit **007 "Sicurezza, privacy e account"**, poi fase **008 "Didattica"**.

### Fase 007: Sicurezza, privacy e account

1. Constitution: principi di sicurezza e privacy per dati di minori e pagamenti (emendamento con
   nuova versione, ADR).
2. Registrazione del titolare con il suo studio. Invito per insegnanti e genitori (link
   firmato a scadenza), così nessuno crea account per conto di altri senza consenso.
3. Verifica email e reset password con token a scadenza e monouso, e risposta identica se
   l'email esiste o no (niente enumerazione degli account).
4. MFA TOTP opzionale per titolari e insegnanti (app di autenticazione, codici di recupero). Nessun SMS.
5. Lockout progressivo dopo N login falliti, oltre al rate limiting che c'è già.
6. Account allievo (maggiorenne) in sola lettura; per un minore, accesso solo tramite il genitore.
7. Consenso del genitore registrato (chi, quando, versione dell'informativa).
8. GDPR: esportazione dei dati di un genitore o allievo (JSON), cancellazione o anonimizzazione con i
   tempi di conservazione (i pagamenti restano per gli obblighi fiscali, anonimizzati), job di retention.
9. Audit log delle azioni sensibili: login, cambio password, MFA, export, cancellazione, pagamenti,
   cambio ruoli.
10. Cifratura applicativa dei campi sensibili (note su minori, telefono), con la chiave da variabile
    d'ambiente e la rotazione documentata.
11. Test IDOR dedicati: insegnante contro allievi di un altro insegnante, genitore contro figli altrui,
    studio contro studio, su ogni endpoint nuovo e su quelli esistenti.
12. Controllo dei segreti nella history git (gitleaks in CI) e verifica dei log senza dati personali.
13. Bozza del **registro dei trattamenti** e dell'**informativa privacy** (da far validare: non è
    consulenza legale).
14. Web e mobile: schermate di registrazione, reset, verifica, MFA, consenso, esportazione e cancellazione.
15. Email transazionali (verifica, reset, inviti) dietro il backend email di Django: in locale
    vanno in console, in produzione usano l'SMTP di B2. Nessun codice dipende dal provider.

### Fase 008: Didattica

16. Ricorrenze delle lezioni (settimanale, con eccezioni), controllo dei conflitti su tutta la serie.
17. Progressi dell'allievo, note di lezione e materiale (file su storage S3-compatibile, non AWS,
    dietro un adapter; in locale su disco).
18. Web e mobile collegati, test dei flussi critici.

### Sempre

- Test, migrazioni, `openapi.yaml` rigenerato, documentazione di studio in italiano, un commit per task.

## B) Cosa serve da te

Ogni voce dice cosa serve, dove si fa e cosa resta già pronto nel codice. I passi esatti sono in
`docs/CHECKLIST_17.md`.

### B0. PostgreSQL su questo PC (adesso, blocca i test)
- **Cosa:** un ruolo PostgreSQL che possa creare il database dei test.
- **Dove:** terminale WSL, con `sudo`.
- **Pronto:** tutto; serve solo `DATABASE_URL`.

### B1. Stripe (sandbox di test)
- **Cosa:** una sandbox dedicata, una chiave ristretta `rk_test_` con "Checkout Sessions: write",
  un endpoint webhook e il suo `whsec_`.
- **Dove:** dashboard.stripe.com.
- **Pronto:** `apps/payments/gateway.py`, webhook su `/api/v1/webhooks/stripe/` per gli eventi
  `checkout.session.completed`, `checkout.session.async_payment_succeeded`,
  `checkout.session.async_payment_failed`, `checkout.session.expired`. Variabili `STRIPE_API_KEY`,
  `STRIPE_WEBHOOK_SECRET`, `STRIPE_WEBHOOK_ALLOWED_IPS` in `.env.example`. Senza chiave il pagamento
  online risponde 503 e il resto funziona. Le chiavi live bloccano l'avvio (ADR-013).
- **Non oggi:** Stripe Connect (pagamenti girati agli insegnanti). Prima va deciso il modello di business.

### B2. Provider email (SMTP)
- **Cosa:** un account presso un provider SMTP con server nell'UE (per esempio Brevo o Mailjet) e il
  dominio mittente verificato (record SPF, DKIM e DMARC).
- **Dove:** sito del provider e pannello DNS del dominio.
- **Pronto:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`,
  `DEFAULT_FROM_EMAIL`. In produzione sono obbligatorie: Coolify blocca il deploy se mancano.

### B3. Dominio e DNS
- **Cosa:** due sottodomini di staging (`api-staging.` e `app-staging.`) che puntano al server Coolify.
- **Dove:** pannello del registrar del dominio.
- **Pronto:** `docker-compose.coolify.yml`, `API_PUBLIC_URL`, `CORS_ALLOWED_ORIGINS`.

### B4. Deploy di staging su Coolify (task aperti T018 e T017)
- **Cosa:** creare la risorsa e incollare le variabili.
- **Dove:** Coolify del tuo amico.
- **Pronto:** `docs/operations/runbook.md`, sezioni "Staging" e "Primo deploy".

### B5. Sentry (facoltativo)
- **Cosa:** un progetto Django e il suo DSN.
- **Dove:** sentry.io, piano gratuito.
- **Pronto:** `SENTRY_DSN`, `SENTRY_ENVIRONMENT`. Se il DSN è vuoto, l'API funziona lo stesso.

### B6. Protezione dei branch su GitHub (fatto il 12 novembre 2026, ruleset, ADR-033)
- **Cosa:** sui branch `main` e `mobile`, rendere obbligatori i check della CI.
- **Dove:** GitHub, Settings, Rules.
- **Pronto:** job `backend`, `frontend`, `web-image` (`ci.yml`) e la CI mobile (`mobile-ci.yml`).

### B7. Store mobile (non oggi)
- **Cosa:** Apple Developer Program (99 USD l'anno), Google Play Console (25 USD una tantum), account Expo per EAS Build.
- **Quando:** dopo la fase 007, quando l'app ha registrazione e privacy complete (gli store chiedono
  l'URL dell'informativa e la procedura di cancellazione dell'account).

### B8. Validazione legale (dopo la fase 007)
- **Cosa:** far leggere a un consulente privacy la bozza del registro dei trattamenti e
  dell'informativa che produrrò nella fase 007.

### Cosa non serve
- **SMS:** l'MFA usa TOTP, quindi niente provider SMS e niente costi.
- **AWS:** lo storage dei materiali (fase 008) usa un bucket S3-compatibile non AWS, lo stesso tipo
  dei backup (ADR-020).
