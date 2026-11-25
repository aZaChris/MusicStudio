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

**API9 — Improper Inventory Management.** *Parziale (alla fase 4; coperto dalla fase 10, vedi sotto).* API versionata (`/api/v1/`), contratto OpenAPI nel repository e controllato dalla CI, ambienti descritti nel runbook. Mancava una politica di deprecazione.

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

## Aggiornamento della fase 8: registro di cassa, istruzioni di pagamento, ricevute

La fase 8 ha aggiunto una dozzina di endpoint su dati di denaro e un IBAN. Lo stato del giro.

**API1 — BOLA. Coperto, con prove sulle rotte nuove.** Lo storno è nella suite IDOR e ha in più una prova contro bersagli già *pagati*: se un attaccante riuscisse a passare, creerebbe davvero uno storno, quindi il test lo vedrebbe. Le rotte senza id (riepilogo, esportazioni, istruzioni) prendono lo studio dal contesto di chi chiama, non da un parametro: non c'è nulla da forzare, e una prova con due studi lo conferma. Le ricevute hanno un loro percorso di visibilità (`RECEIPT_PATHS` in `scoping.py`): il genitore vede solo quelle del proprio figlio, anche se un fratello è nello stesso studio. La guardia `test_idor_coverage.py` ha costretto a dichiarare ogni rotta nuova.

**API3 — Proprietà degli oggetti. Coperto.** `reversal_of`, `reason`, `recorded_by` e `receipt_number` sono in sola lettura, e un client non può creare uno storno scrivendo `status=reversal`. Genitori e studenti adulti non ricevono `reason` né `recorded_by`.

**API4 — Risorse. Coperto, con un bug trovato.** Le esportazioni coprono al massimo 366 giorni e hanno un limite di frequenza dedicato (`register_export`). Scrivendo il test è emerso un difetto: nei settings di test il tasso non esisteva, e il throttle "fail open" (che per scelta lascia passare se qualcosa non va) lasciava passare le esportazioni senza limite e senza dire nulla. Ora il tasso è nei settings di test e un test controlla che esista anche in quelli di produzione.

**API5 — Funzioni. Coperto.** Il registro, lo storno, le esportazioni e le ricevute sono per insegnanti e titolari: una nuova classe di permesso rifiuta genitori e studenti adulti anche in lettura (quella vecchia lasciava leggere chiunque fosse autenticato). Le istruzioni le modifica solo il titolare.

**Iniezione. Coperto.** I testi scritti da persone nell'esportazione CSV (studente, motivo) che iniziano con `=`, `+`, `-` o `@` ricevono un apostrofo davanti: un foglio di calcolo non li esegue come formule.

**SSRF. Non applicabile, per costruzione.** I link di pagamento si salvano e si mostrano, il server non li apre mai. Sono accettati solo `https`, e nel portale si aprono con `rel="noopener noreferrer"`.

**Dati sensibili. Coperto.** Intestatario e IBAN sono cifrati nel database. Il corpo delle richieste a `/payment-instructions/` è tra i percorsi sensibili di Sentry. Il registro delle azioni riceve solo i nomi dei campi cambiati. Un test manda un IBAN in una richiesta rifiutata e in una che manda in errore il server, ed esegue i flussi nuovi catturando tutti i log: non trova né l'IBAN, né l'intestatario, né i nomi, né il motivo di uno storno.

**Ancora aperto.** La regola "definitivo" sta nei service: un aggiornamento di massa sul database la aggirerebbe. Un test lo sorveglia, ma non è una garanzia del database. La frase "non è un documento fiscale" e i termini d'uso vanno fatti controllare da un professionista. Il titolare, gli insegnanti e i genitori vedono l'IBAN in chiaro, perché è lo scopo. La prova di carico è su un portatile, non su un server.

## Aggiornamento della fase 9: pagamenti sul conto dello studio

La fase 9 ha aggiunto il conto Stripe dello studio, un secondo webhook e rimborsi e contestazioni nel registro. Tutto dietro un interruttore spento di default. Lo stato del giro.

**API1 — BOLA. Coperto.** Le quattro rotte del conto (`/payment-account/`, `onboarding`, `refresh`, `restart`) non hanno un id: lo studio è sempre quello di chi chiama, e una prova con due studi mostra che ognuno vede e tocca solo il proprio. Sono nella suite IDOR. Per gli eventi di Stripe l'isolamento sta nell'attribuzione: l'evento porta l'id del conto, e il pagamento a cui si riferisce un rimborso si cerca per id del pagamento Stripe **e** per conto. Un test manda un evento del conto di uno studio con l'id di un pagamento di un altro: non cambia nulla.

**API3 — Proprietà degli oggetti. Coperto.** `cause` è in sola lettura e le righe di storno non si creano dall'API: un test legge il codice e fallisce se una riga di `Payment` nasce fuori dai service.

**API4 — Risorse. Coperto.** Onboarding e rilettura del conto hanno un limite di frequenza (`payment_account`), con la tariffa nei settings di test (un test lo controlla, per non ripetere il bug del throttle che "fail open" delle esportazioni). Il giro orario che rilegge i conti ha un tetto di 200 conti e un errore su uno non ferma gli altri.

**API5 — Funzioni. Coperto.** Solo il titolare avvia, rilegge e riavvia il conto; gli insegnanti leggono; genitori e studenti non hanno accesso.

**API8 — Configurazione. Coperto.** L'interruttore `ONLINE_PAYMENTS_ENABLED` è spento di default e, spento, le rotte rispondono 404. Una chiave `sk_live_` blocca ancora l'avvio. Un evento con `livemode` vero si conserva e si ignora.

**API10 — Uso non sicuro di API di terzi. Coperto, con un limite.** I due webhook hanno ognuno il suo segreto e non accettano la firma dell'altro. L'indirizzo di provenienza è controllato per entrambi. Gli eventi si salvano una volta e si elaborano una volta, e un evento di un conto sconosciuto o diverso da quello del tentativo non chiude nulla. La versione salvata di un evento è ripulita da nomi, email, indirizzi e dati di carta, e si cancella dopo 90 giorni. Il limite: **non ho eventi veri di Stripe**, solo eventi con la forma della documentazione.

**Dati sensibili. Coperto.** Del conto salviamo solo l'id e uno stato; nessun dato personale va a Stripe (nemmeno l'email del titolare, che la inserisce lì). Un test percorre il flusso del conto catturando i log e non trova né email né nome dello studio.

**Ancora aperto.** Il pagamento diretto, un rimborso e una contestazione non sono stati provati su Stripe vero: servono un conto di prova attivato e la verifica della forma degli eventi. PayPal non è verificato. Che i parametri dell'API nuova corrispondano al modello "Stripe fattura le commissioni" va confermato nella Dashboard. I termini d'uso e la frase delle ricevute restano da far validare. Per andare con soldi veri servono un emendamento alla costituzione e una decisione del titolare.

## Aggiornamento della fase 10: versionamento, admin ed export

La fase 10 non aggiunge funzioni per gli utenti: chiude il rischio rimasto parziale e la porta più grande del sistema, l'admin. Lo stato del giro.

**API9 — Gestione dell'inventario. Ora coperto.** C'è una politica scritta di versionamento e deprecazione (`docs/operations/api-versioning-policy.md`, 90 giorni di preavviso). Un endpoint deprecato porta `Deprecation`, `Sunset` e `Link` in ogni risposta, è segnato nel contratto e dopo la data risponde 410. Un registro controllato da un test e un workflow settimanale che diventa rosso a 30 giorni dalla rimozione tengono d'occhio le date. In CI, `oasdiff` confronta il contratto con quello di `main` e blocca le modifiche incompatibili non dichiarate: rinominare un campo di `Lesson` in una copia di prova dà 10 errori. Il limite: i valori nuovi negli enum di risposta passano come avvisi, e la policy chiede ai client di gestire i valori sconosciuti (ADR-040).

**API8 — Configurazione. Coperto, con un buco chiuso.** L'admin era quello predefinito di Django: bastava `is_staff`. Ora entra solo un operatore (staff senza ruolo di studio), con il TOTP in produzione e gli stessi blocchi dell'accesso API. Chi non è operatore riceve 404. Si può limitare per indirizzo IP, e ogni accesso è nel registro. Il test d'inventario dell'admin ha trovato le tabelle dei token di simplejwt, registrate in automatico e con i refresh token interi: tolte (ADR-041).

**API5 — Funzioni. Coperto.** Dall'admin non si scrivono più pagamenti, ricevute, consensi, registro, lezioni, pacchetti o studenti. L'unico modello modificabile, l'utente, registra chi ha cambiato quali campi, senza i valori. Un test per ogni ruolo di studio prova il 404, anche con `is_staff` forzato.

**Dati sensibili. Coperto.** Nessuna schermata dell'admin mostra un campo cifrato (note, motivo di uno storno, IBAN, segreti MFA): un test lo controlla su ogni modello registrato. L'export GDPR ha ora un inventario di tutti i modelli, e un test fallisce su un modello che nessuno ha deciso se esportare. L'analisi ha trovato sette buchi, tutti chiusi (ADR-042).

**Ancora aperto.** Il conteggio delle chiamate agli endpoint deprecati è "unknown" finché i log non stanno in un archivio interrogabile. Il primo deploy si fa con il TOTP dell'admin spento, si attiva quello dell'operatore e poi si riaccende l'obbligo: altrimenti l'operatore resta fuori.

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

5. **Qual era l'ultimo rischio rimasto parziale, e come si è chiuso?**
   API9: mancava una politica di deprecazione delle versioni dell'API. La fase 10 l'ha aggiunta, con segnali in ogni risposta, un registro con promemoria e un controllo del contratto in CI (ADR-040).
