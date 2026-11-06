# Sicurezza delle API: la OWASP API Security Top 10

## TL;DR

La OWASP API Security Top 10 è la lista dei dieci rischi di sicurezza più comuni nelle API. La constitution di MusicStudio chiede di verificarla alla fine di ogni fase. Questo documento la spiega e registra lo stato aggiornato alla fine della fase 2: cosa è coperto, cosa è parziale, cosa è aperto. Interventi principali: scritture cross-tenant chiuse e rate limiting sul login (fase 1); tenant esplicito, permessi per oggetto e stati dei pagamenti (fase 2).

## Il problema reale

Un'API è una porta aperta su Internet. Chiunque può mandare richieste, anche costruite a mano, saltando l'interfaccia grafica. Tutto quello che il frontend "non mostra" è comunque raggiungibile.

La sicurezza spesso viene rimandata: "la sistemiamo prima del lancio". Ma una revisione fatta una volta sola, alla fine, trova i problemi quando correggerli costa di più. Per questo la regola è verificare la lista alla fine di ogni fase. E non per spuntare caselle: per costringersi a guardare l'API come la guarderebbe un attaccante.

## Come funziona

Pensa all'ispezione periodica di un edificio. L'ispettore ha una lista: uscite di emergenza, estintori, impianto elettrico. Non inventa i controlli ogni volta: segue la lista, e per ogni voce scrive "conforme", "da migliorare" o "non conforme". La OWASP Top 10 è la lista dell'ispettore per le API.

Una caratteristica importante delle API è che molti attacchi non sono tecnicamente sofisticati. Non serve rompere la crittografia. Basta cambiare un numero in una URL, mandare un campo in più nel JSON o fare mille richieste al secondo. Per questo i primi rischi della lista riguardano l'autorizzazione e i limiti, non la crittografia.

Il **rate limiting** merita una spiegazione a parte. Limita quante richieste un client può fare in un intervallo di tempo. Sul login protegge dal brute force, cioè dal provare migliaia di password. In generale protegge dal consumo di risorse. DRF lo implementa con i "throttle": contano le richieste in una cache condivisa e, oltre il limite, rispondono 429 Too Many Requests con un'intestazione `Retry-After`.

## Come lo abbiamo applicato in MusicStudio

Ecco lo stato alla fine della fase 2, voce per voce.

**API1 — Broken Object Level Authorization.** *Coperto.* Le letture erano già filtrate per tenant. Le scritture no: un insegnante poteva creare lezioni e pagamenti sugli allievi di un altro. Ora i campi di relazione sono filtrati per utente (`backend/apps/common/serializers.py`) e ogni endpoint di scrittura ha un test cross-tenant. Nella fase 2 lo studio è diventato un tenant obbligatorio, e un permesso per oggetto (`CanWriteTenantObject`) ricontrolla ogni modifica.

**API2 — Broken Authentication.** *Parziale.* JWT con token di accesso di 60 minuti e refresh con rotazione. Login limitato a 5 tentativi al minuto per client. Manca: la blacklist dei refresh token dopo la rotazione, il logout lato server e l'MFA. La chiave di firma in produzione è obbligatoria e separata dalla `SECRET_KEY`.

**API3 — Broken Object Property Level Authorization.** *Coperto.* `lessons_remaining`, `teacher`, `studio`, `end_time` e lo stato della lezione sono in sola lettura. L'insegnante di un allievo si cambia solo con l'azione riservata al titolare. Lo stato di un pagamento segue una macchina a stati, e «pagato» è finale.

**API4 — Unrestricted Resource Consumption.** *Coperto per la fase 1.* Throttle globali (100 richieste l'ora da anonimi, 1000 da autenticati) e uno specifico per il login, configurabili da variabili d'ambiente. Paginazione a 25 elementi. Le query hanno un numero costante, quindi una richiesta non può far lavorare il database in proporzione ai dati. La configurazione è in `backend/config/settings/base.py`:

```python
"DEFAULT_THROTTLE_RATES": {
    "anon": env("THROTTLE_ANON", default="100/hour"),
    "user": env("THROTTLE_USER", default="1000/hour"),
    "login": env("THROTTLE_LOGIN", default="5/min"),
},
```

E la view di login in `backend/apps/accounts/views.py` usa `ScopedRateThrottle` con lo scope `login`. Il test `test_login_is_throttled_after_five_attempts` verifica che il sesto tentativo riceva 429. I contatori stanno nella cache Redis, condivisa da tutti i processi web: con una cache in memoria ogni processo avrebbe il suo contatore e il limite si moltiplicherebbe.

**API5 — Broken Function Level Authorization.** *Coperto.* Le azioni di scrittura richiedono il ruolo insegnante o titolare; lo studio e lo spostamento degli allievi sono solo per i titolari; i genitori sono in sola lettura. Ogni ruolo ha un test per l'azione di spostamento.

**API6 — Unrestricted Access to Sensitive Business Flows.** *Non applicabile oggi.* Non ci sono flussi come acquisti o prenotazioni pubbliche. Diventerà rilevante con Stripe nella fase 3.

**API7 — Server Side Request Forgery.** *Non applicabile.* L'API non scarica URL fornite dagli utenti.

**API8 — Security Misconfiguration.** *Coperto per la fase 1.* `DEBUG` disattivo in produzione, host ammessi espliciti, HSTS, cookie sicuri, redirect HTTPS dietro proxy, `nosniff`, admin su un path configurabile. La produzione non parte senza segreti. Verificato avviando gunicorn: host sconosciuto 400, HTTP 301, intestazioni di sicurezza presenti.

**API9 — Improper Inventory Management.** *Parziale.* L'API è versionata (`/api/v1/`) e il contratto OpenAPI è salvato nel repository: la CI fallisce se il codice lo cambia senza aggiornarlo. Manca una politica di deprecazione: fase 5.

**API10 — Unsafe Consumption of APIs.** *Non applicabile oggi.* Nessuna API esterna. Lo diventerà con i webhook di Stripe, che andranno verificati con la firma.

**Altro.** Nessun segreto nel repository. Il comando `seed_demo`, che crea utenti con password nota, si rifiuta di girare con `DEBUG=False`. Il linter controlla anche alcune regole di sicurezza di bandit.

## Alternative considerate

**django-axes** per il login: blocca l'account dopo N errori. Ma permette a chiunque conosca un'email di bloccare quell'account (un piccolo denial of service). Il rate limiting per client non ha questo effetto.

**Rate limiting nel proxy** (Traefik di Coolify). Protegge anche prima di Django, ma non si testa in CI e non è portabile. Si può aggiungere sopra, più avanti.

**Un WAF esterno.** Utile su larga scala, sproporzionato oggi.

## Errori comuni e trade-off

- **Throttle con cache locale per processo.** Ogni worker conta da solo e il limite reale si moltiplica.
- **Identificare il client per IP dietro un proxy.** Se il proxy non è configurato bene, tutti sembrano venire dallo stesso IP, o un attaccante falsifica l'intestazione. Va verificato al deploy reale, nella fase 4.
- **Pensare che l'autenticazione basti.** Quasi tutti i rischi della lista riguardano utenti autenticati che fanno cose che non dovrebbero.
- **Trade-off:** limiti troppo stretti bloccano utenti legittimi, come una scuola con molti insegnanti dietro lo stesso IP. Per questo sono configurabili.

## Come lo spiegheresti a un colloquio

Alla fine di ogni fase verifico l'API contro la OWASP API Security Top 10 e registro cosa è coperto e cosa no. Nella fase 1 il problema più serio era il primo della lista, BOLA: le scritture non erano filtrate per tenant, e l'ho corretto con test dedicati per ogni endpoint. Per il consumo di risorse ho aggiunto throttle globali e uno stretto sul login, con i contatori in Redis condivisi tra i processi. In produzione la configurazione è sicura di default e l'applicazione non parte senza segreti. Nella fase 2 ho reso lo studio un tenant esplicito e aggiunto permessi per oggetto. Restano aperti, e documentati, la revoca dei token e i flussi legati ai pagamenti, che arriveranno con Stripe.

## Domande di autoverifica

1. **Qual è il rischio numero uno della OWASP API Top 10, e come si è presentato in MusicStudio?**
   BOLA. I campi di relazione accettavano id di altri tenant, quindi un insegnante poteva scrivere sugli allievi di un altro.

2. **Perché i contatori del rate limiting stanno in Redis e non in memoria?**
   Perché con più processi web ogni processo avrebbe il suo contatore, e il limite reale sarebbe moltiplicato.

3. **Perché non abbiamo bloccato l'account dopo N tentativi?**
   Perché permetterebbe a chiunque di bloccare un account conoscendone solo l'email.

4. **Cosa resta aperto per l'autenticazione?**
   La blacklist dei refresh token, il logout lato server e l'MFA.

5. **Quali rischi diventeranno rilevanti con Stripe?**
   API6 per i flussi di acquisto e API10 per i webhook, che andranno verificati con la firma e resi idempotenti.
