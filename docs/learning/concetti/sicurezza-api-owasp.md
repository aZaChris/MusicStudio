# Sicurezza delle API: la OWASP API Security Top 10

## TL;DR

La OWASP API Security Top 10 è la lista dei dieci rischi di sicurezza più comuni nelle API. La constitution di MusicStudio chiede di verificarla alla fine di ogni fase. Questo documento registra lo stato alla fine della fase 4: tutti e dieci i rischi hanno un verdetto e una prova. La fase 4 ha chiuso la revoca dei token, ha aggiunto l'allowlist IP sul webhook di Stripe e, durante il giro, ha trovato e corretto un bug vero: il limite sui tentativi di login si poteva aggirare.

## Il problema reale

Un'API è una porta aperta su Internet. Chiunque può mandare richieste costruite a mano, saltando l'interfaccia grafica. Tutto quello che il frontend "non mostra" è comunque raggiungibile.

La sicurezza spesso viene rimandata a "prima del lancio". Ma una revisione fatta una volta sola trova i problemi quando correggerli costa di più. Per questo la regola è ripetere il giro a ogni fase, guardando l'API come la guarderebbe un attaccante. Il giro di questa fase lo dimostra: un difetto presente dalla fase 1 è emerso solo rileggendo il codice con la lista in mano.

## Come funziona

Pensa all'ispezione periodica di un edificio. L'ispettore ha una lista: uscite di emergenza, estintori, impianto elettrico. Per ogni voce scrive "conforme", "da migliorare" o "non conforme", e allega la prova. La OWASP Top 10 è la lista dell'ispettore per le API.

Molti attacchi alle API non sono sofisticati. Basta cambiare un numero nella URL, mandare un campo in più nel JSON, fare mille richieste al secondo, o scrivere un'intestazione falsa. Per questo i primi rischi della lista riguardano autorizzazione e limiti, non crittografia.

## Come lo abbiamo applicato in MusicStudio

Ecco lo stato alla fine della fase 4, voce per voce.

**API1 — Broken Object Level Authorization.** *Coperto.* Letture e scritture sono filtrate per tenant (`backend/apps/common/scoping.py`, `TenantContext`). Ogni endpoint di scrittura ha un test cross-tenant. Il nuovo logout rifiuta il refresh token di un altro utente con lo stesso errore di un token malformato, così non rivela niente.

**API2 — Broken Authentication.** *Coperto* (era parziale). Il refresh token ruota, e quello vecchio finisce in una lista nera: chi ne riusa una copia riceve 401. Il logout rende subito inutilizzabile il refresh token del dispositivo. Un operatore può revocare tutte le sessioni di un account. Il token di accesso dura 15 minuti invece di 60, perché non viene controllato contro la lista (ADR-018). Login limitato a 5 tentativi al minuto. L'autenticazione a due fattori è arrivata nella fase 7 (vedi l'aggiornamento più sotto).

**API3 — Broken Object Property Level Authorization.** *Coperto.* I campi derivati (`lessons_remaining`, `end_time`, studio, insegnante) sono in sola lettura. Lo stato di un pagamento segue una macchina a stati.

**API4 — Unrestricted Resource Consumption.** *Coperto, con una correzione in questa fase.* Throttle globali e uno stretto sul login, paginazione fissa a 25, query in numero costante. Il bug: i throttle di DRF identificano il client con l'intestazione `X-Forwarded-For`, e senza l'impostazione `NUM_PROXIES` usano **tutta** l'intestazione, che scrive il client. Bastava cambiarla a ogni tentativo per avere un contatore nuovo. Ora `NUM_PROXIES` segue `TRUSTED_PROXY_COUNT`:

```python
TRUSTED_PROXY_COUNT: int = env.int("TRUSTED_PROXY_COUNT", default=0)
REST_FRAMEWORK = {
    # ...
    "NUM_PROXIES": TRUSTED_PROXY_COUNT,
}
```

Il test `test_forged_forwarded_for_cannot_reset_the_login_throttle` manda sei tentativi con origini false: prima della correzione erano sei 401, ora il sesto è 429. Il load test con 50 utenti ha dato zero errori e ha misurato che un login costa circa 2 secondi di CPU su un portatile. Anche per questo il limite sul login conta.

**API5 — Broken Function Level Authorization.** *Coperto.* Scritture solo per insegnanti e titolari, genitori in sola lettura. La revoca di tutte le sessioni è un comando e un'azione dell'admin, non un endpoint pubblico.

**API6 — Unrestricted Access to Sensitive Business Flows.** *Coperto.* Un pacchetto pagato non si ripaga, un doppio clic riusa lo stesso tentativo, il pagamento si registra solo dal webhook.

**API7 — Server Side Request Forgery.** *Non applicabile.* L'API non scarica URL fornite dagli utenti. Le chiamate in uscita (Stripe, Sentry, il bucket dei backup) hanno destinazioni fissate nella configurazione.

**API8 — Security Misconfiguration.** *Coperto.* `manage.py check --deploy` gira ora in CI con i settings di produzione: una configurazione insicura blocca la build. Sentry è attivo solo con un DSN e toglie token, cookie, firme ed email prima di inviare. L'header `X-Request-ID` del client viene accettato solo se fatto di lettere, numeri e trattini, così nessuno può iniettare righe false nei log. La readiness non mostra mai il testo delle eccezioni. Una sola eccezione voluta: il preload HSTS è disattivato, perché impegna tutto il dominio ed è una decisione del proprietario.

**API9 — Improper Inventory Management.** *Parziale.* API versionata (`/api/v1/`), contratto OpenAPI nel repository e controllato dalla CI, ambienti descritti nel runbook. Manca una politica di deprecazione: fase 5.

**API10 — Unsafe Consumption of APIs.** *Coperto.* I webhook di Stripe passano due controlli: l'indirizzo deve essere nella lista pubblicata da Stripe, e la firma deve essere valida. L'indirizzo è quello vero, calcolato contando i proxy fidati da destra di `X-Forwarded-For` (ADR-021). Un test prova che un'origine falsificata a sinistra viene rifiutata.

**Il portale web.** Dal 10 novembre 2026 il giro copre anche la SPA in `frontend/`. Contro l'XSS: React mostra i dati come testo, e una Content-Security-Policy stretta permette script solo dal portale e connessioni solo verso le API. Il token di accesso sta in memoria; il refresh token in `localStorage` è un rischio accettato e documentato (ADR-023), con il cookie httpOnly come passo successivo. Le API accettano chiamate dal browser solo dall'origine del portale. Dettagli in `concetti/sicurezza-di-una-spa.md`.

## Aggiornamento della fase 7: account, privacy e sicurezza

La fase 7 ha aggiunto account veri (registrazione, reset, inviti), quindi il giro cambia in più punti. Lo stato è questo.

**API1 — BOLA. Coperto, ora con la prova.** Prima di toccare l'autenticazione abbiamo scritto una suite sistematica: 11 coppie attaccante/vittima (altro insegnante dello stesso studio, altro studio, altra famiglia, uno studente adulto contro i compagni) contro ogni lettura, scrittura e azione. Sono 322 casi, e **non ha trovato nessuna falla**. Un test di guardia percorre le rotte di `/api/v1/` e fallisce se ne compare una nuova che non è nella suite o dichiarata senza dati di tenant. Le rotte nuove (privacy, audit, MFA, inviti) sono state aggiunte con i loro test sulle famiglie e sugli studi diversi.

**API2 — Broken Authentication. Rafforzato.** Blocco dell'account dopo cinque password sbagliate, con durata che raddoppia fino a 24 ore. Verifica in due passaggi TOTP per titolari e insegnanti. Risposte uguali per email esistente e non esistente, in registrazione, reinvio e reset. Link di conferma e reset a uso singolo. Nuova password o reset: tutte le sessioni finiscono. Un test verifica che l'account non confermato non possa accedere.

**API3 — Property level. Coperto.** `has_account` è in sola lettura. `is_adult` si può togliere solo se l'allievo non ha ancora un account, così un minore non ne ottiene uno.

**API4 — Risorse. Coperto.** Le rotte nuove hanno i loro limiti di frequenza (`register`, `password_reset`, `mfa`, `privacy`, `invitation_accept`).

**API5 — Funzioni. Coperto.** Il registro delle azioni lo legge solo il titolare. L'esportazione e la cancellazione sono per genitori e studenti adulti. Un titolare può cancellarsi solo con lo studio vuoto.

**API8 — Configurazione. Coperto, con un bug trovato.** Un test ora esegue i flussi di account catturando tutti i log e cerca ogni valore digitato o spedito. Ha trovato che **Celery scriveva il token d'invito in chiaro** nel log di fine task, e che il nostro formatter JSON lo avrebbe stampato in produzione. Corretto con un filtro sul logger di Celery (vedi `docs/knowledge-base/celery-scrive-i-token-nei-log.md`). Altri test fissano HSTS, cookie sicuri e il rifiuto di partire senza la chiave di cifratura. Una scansione dei segreti su tutta la cronologia è in CI (gitleaks, versione e checksum fissati). Durante la fase, il passo `check --deploy` della CI mancava delle due nuove variabili obbligatorie: corretto prima che bloccasse la build.

**Dati sensibili.** Le note delle lezioni e il segreto TOTP sono cifrati nel database (ADR-030). Il registro delle azioni contiene solo identificativi (ADR-031). Un test cerca nome ed email di una persona cancellata in tutte le colonne di testo.

**Ancora aperto.** Il refresh token del portale in cookie httpOnly. La prova della scansione dei segreti in locale: nel mio ambiente non ho potuto eseguire il binario di gitleaks, quindi la prima esecuzione la farà la CI.

## Alternative considerate

**django-axes** per il login: blocca l'account dopo N errori. Ma chiunque conosca un'email potrebbe bloccare quell'account. Il limite per client non ha questo effetto.

**Allowlist e rate limiting nel proxy** (Traefik di Coolify). Agiscono prima di Django, ma stanno fuori dal repository e fuori dai test.

**Un WAF esterno.** Utile su larga scala, sproporzionato oggi.

## Errori comuni e trade-off

- **Fidarsi dei default delle librerie per l'IP del client.** Il bug di questa fase viene da lì. Ogni componente che "trova l'IP" va controllato.
- **Testare solo il caso normale.** Il vecchio test sul login non mandava mai `X-Forwarded-For`, quindi passava. Un test di sicurezza deve provare anche l'attacco.
- **Throttle con cache locale per processo.** Ogni worker conta da solo e il limite si moltiplica.
- **Trade-off sui token:** dopo il logout, un token di accesso già emesso funziona ancora per al massimo 15 minuti. Controllarlo a ogni richiesta costerebbe una query.
- **Trade-off sulla disponibilità:** con Redis giù i throttle lasciano passare. Meglio un'API senza limiti per qualche minuto che un'API spenta.

## Come lo spiegheresti a un colloquio

Alla fine di ogni fase verifico l'API contro la OWASP API Security Top 10 e registro, per ogni rischio, un verdetto e la prova. Nella fase 4 ho chiuso la revoca dei token con una lista nera dei refresh token, la rotazione e un token di accesso di 15 minuti. Durante il giro ho trovato che il limite sul login si poteva aggirare cambiando `X-Forwarded-For`, perché DRF senza `NUM_PROXIES` usa tutta l'intestazione, e l'ho corretto con un test che prova l'attacco. Ho aggiunto i controlli di deploy di Django in CI e l'allowlist degli IP di Stripe, calcolando l'IP reale dietro il proxy. Resta aperta solo la politica di deprecazione delle API, prevista nella fase 5.

## Domande di autoverifica

1. **Come si aggirava il limite sui tentativi di login, e come l'abbiamo chiuso?**
   Mandando un `X-Forwarded-For` diverso a ogni tentativo: senza `NUM_PROXIES`, DRF usava tutta l'intestazione come identità. Ora `NUM_PROXIES` segue il numero di proxy fidati.

2. **Perché dopo il logout il token di accesso funziona ancora per un po'?**
   Perché solo i refresh token sono nella lista nera. Controllare anche quelli di accesso costerebbe una query a ogni richiesta; per questo durano solo 15 minuti.

3. **Perché si legge l'IP da destra in `X-Forwarded-For`?**
   Perché ogni proxy aggiunge in fondo l'indirizzo da cui riceve la connessione. Quello che sta a sinistra l'ha scritto il client e può essere falso.

4. **Cosa controlla `check --deploy` in CI?**
   Le impostazioni di sicurezza di Django in produzione: `DEBUG`, HSTS, cookie sicuri, redirect HTTPS, chiave segreta. Un problema fa fallire la build.

5. **Qual è l'unico rischio ancora parziale, e perché?**
   API9: manca una politica di deprecazione delle versioni dell'API. È prevista nella fase 5.
