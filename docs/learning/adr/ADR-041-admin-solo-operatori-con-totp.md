# ADR-041: L'admin è solo per gli operatori, con TOTP, record in sola lettura e audit

- Stato: accettato
- Data: 2026-11-25

## Contesto

L'admin di Django è l'unico posto che salta l'isolamento per studio: vede i dati di tutti. Fino alla fase 9 era quello predefinito. Bastava un account `is_staff` per entrare, i pagamenti si potevano modificare e cancellare (`admin.site.register(Payment)`), e nessuna modifica finiva nel registro. Una password di operatore rubata, o un clic distratto, era il peggior incidente possibile.

## Decisione

- **Chi è un operatore**: un utente attivo, `is_staff` e **senza ruolo di studio** (`role` vuoto, come gli account creati con `createsuperuser`). È la proprietà `User.is_operator`. Un insegnante o un titolare non passa nemmeno con `is_staff` forzato.
- **Un `OperatorAdminSite`** (`apps/common/admin_site.py`) diventa `admin.site` tramite `OperatorAdminConfig.default_site`. Così i `@admin.register` esistenti non cambiano. La configurazione sta in un modulo a parte, `admin_config.py`: con due `AppConfig` nello stesso `apps.py`, Django non sa quale scegliere.
- **404, non 403**, per chi non è operatore e per gli indirizzi fuori da `ADMIN_ALLOWED_IPS` (lista vuota = nessuna restrizione): l'admin non conferma nemmeno di esistere.
- **TOTP in produzione** (`ADMIN_REQUIRE_TOTP`, vero per default in `prod`). Il login dell'admin ha un campo in più per il codice, controllato con il servizio MFA già esistente (`check_second_factor`, che accetta anche i codici di recupero). Gli operatori diventano "eleggibili" per la MFA e la attivano con gli stessi endpoint dell'API.
- **Stesso blocco dell'API**: password o codice sbagliati passano da `register_login_failure`. Un account bloccato riceve lo stesso messaggio generico di una password sbagliata. Ogni accesso, riuscito o no, scrive `admin.login`.
- **Due regole per i modelli** (`apps/common/admin_mixins.py`):
  - `ReadOnlyAdmin` per i record definitivi (pagamenti, ricevute, contestazioni, checkout, eventi Stripe, consensi, registro) e per i dati che cambiano solo dai service (lezioni, pacchetti, studenti, studi, promemoria);
  - `AuditedAdmin` per l'unico modello modificabile, l'utente. Ogni salvataggio scrive `admin.change` con i **nomi** dei campi cambiati, mai i valori. Le cancellazioni scrivono `admin.delete`, con il conteggio se sono in blocco. Le azioni personalizzate passano da `audited_action`.
- **Nessun campo cifrato a schermo**: note delle lezioni, motivo di uno storno, IBAN e segreti MFA. Istruzioni di pagamento, conto collegato, dispositivi MFA e codici di recupero non sono registrati.
- Il recupero di un operatore che perde il telefono è il comando `reset_mfa` della fase 7, già registrato nell'audit. Non è una schermata.

## Alternative scartate

- **`django-otp` o `django-two-factor-auth`**: una seconda implementazione TOTP accanto alla nostra, con template da mantenere.
- **Solo VPN o autenticazione del proxy**: non è sotto il nostro controllo; resta utile come strato in più.
- **Togliere l'admin e usare solo comandi**: l'operatore perderebbe la vista in sola lettura che usa per l'assistenza.
- **Rendere modificabili lezioni e pacchetti**: un salvataggio dall'admin salterebbe i controlli di `services.py` (sovrapposizioni, saldo, limite di insegnanti). È la scelta più prudente; se un giorno servisse correggere qualcosa a mano, si farà con un comando che passa dai service.
- **Il `LogEntry` di Django**: il superuser può modificarlo, e duplica il registro.

## Conseguenze

- Il test d'inventario (`test_admin_inventory.py`) ha trovato subito una cosa vera: `simplejwt` registra da solo le sue tabelle `OutstandingToken` e `BlacklistedToken`, che contengono i refresh token interi. Ora sono tolte dall'admin, insieme ai `Group` di Django che non usiamo.
- **Attenzione al deploy**: con `ADMIN_REQUIRE_TOTP` vero per default, un operatore che non ha ancora attivato il TOTP non entra più nell'admin. Non si può attivarlo prima del deploy, perché è questa fase a rendere gli operatori idonei alla MFA. Quindi il primo deploy si fa con `ADMIN_REQUIRE_TOTP=false`, si attiva il TOTP tramite l'API, poi si toglie la variabile e si rideploya (runbook). Nella prima stesura avevo scritto "attivarlo prima del deploy": era sbagliato, e l'ho corretto rileggendo i passi del deploy.
- Un account creato con `createsuperuser` ha l'email non confermata, e il login dell'API lo rifiuta: per attivare il TOTP l'operatore deve prima confermare l'email con il flusso esistente ("rinvia la conferma"). Il runbook lo spiega passo per passo. Non abbiamo aggiunto un comando apposta: il percorso c'è già, ed è lo stesso di tutti gli altri account.
- Un vecchio test usava un insegnante con `is_staff` come "operatore": ora riceve 404, ed è stato aggiornato.
