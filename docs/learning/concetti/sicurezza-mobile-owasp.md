# Sicurezza dell'app: la OWASP Mobile Top 10

## TL;DR

La OWASP Mobile Top 10 è la lista dei dieci rischi più comuni nelle app mobili. Come per il backend, la constitution del mobile chiede di percorrerla alla fine di ogni fase e di registrare, per ogni voce, un verdetto e una prova. Questo è lo stato alla fine della fase 1 del refactor mobile. I punti forti sono la gestione della sessione e il fatto che l'app non contiene segreti. I punti aperti sono la catena delle dipendenze, con 24 segnalazioni di `npm audit` di cui 2 nel bundle, e l'assenza di una prova su un telefono vero.

## Il problema reale

Un'app mobile si installa sul telefono di chiunque. Chi vuole attaccarla può scaricarla, aprirla, leggerne il codice e osservare il traffico. Quindi tutto quello che sta nell'app va considerato pubblico. E il telefono può essere perso, rubato o condiviso tra genitori e figli.

Per MusicStudio la domanda è concreta. L'app mostra dati di minori e pagamenti. Cosa succede se un telefono viene perso con la sessione aperta? E se qualcuno estrae il token? E se due persone usano lo stesso telefono?

## Come funziona

Pensa a una cassetta delle chiavi in un condominio. La cassetta è nell'atrio, chiunque la vede. Una cosa la puoi decidere: cosa ci metti dentro e quanto valgono le chiavi. Una chiave che apre solo il tuo appartamento e scade dopo 15 minuti vale poco a chi la ruba. Un passe-partout permanente vale tutto.

La OWASP Mobile Top 10, nella versione del 2024, è la lista dei controlli da fare su quella cassetta. Molte voci non riguardano la crittografia ma scelte semplici: dove salvi le credenziali, cosa mostri, di chi ti fidi.

## Come lo abbiamo applicato in MusicStudio

**M1 — Improper Credential Usage.** *Coperto.* Nessuna credenziale nel codice. L'unica configurazione è l'indirizzo delle API, in `EXPO_PUBLIC_API_BASE_URL`, e `.env.example` spiega che tutto quello che inizia con `EXPO_PUBLIC_` finisce nel bundle pubblico. I token arrivano solo dal login dell'utente.

**M2 — Inadequate Supply Chain Security.** *Parziale.* Le dipendenze sono bloccate nel `package-lock.json`, installate con `npm ci` in CI e aggiunte con `npx expo install`, che sceglie versioni compatibili con l'SDK. Ma `npm audit` segnala 24 vulnerabilità nelle dipendenze di produzione (1 critica, 7 alte). Quasi tutte, compresa la critica in `shell-quote`, stanno negli strumenti della CLI di Expo, che girano sul computer di chi sviluppa e non nell'app. Due però finiscono nel bundle: `decode-uri-component` e `query-string`, usate da `expo-router` per leggere i link. Il rischio è un blocco dell'app con un link malformato. La correzione richiede una versione di `expo-router` fuori da quella allineata all'SDK 57: è un rischio accettato e aperto, da chiudere con `npx expo install --fix` quando esce una patch dell'SDK. Non abbiamo usato `npm audit fix --force`, che romperebbe l'allineamento con l'SDK.

**M3 — Insecure Authentication/Authorization.** *Coperto.* L'autorizzazione la decide il backend, non l'app: è il primo principio della constitution. L'app non deduce permessi dal ruolo salvato. All'avvio chiede `GET /auth/me/`, gestisce 401, 403 e 404 in modo esplicito, e il portale dei genitori non offre nessuna azione di scrittura. Un test lo verifica: l'unico pulsante nel portale è "Esci".

**M4 — Insufficient Input/Output Validation.** *Coperto per quello che spetta all'app.* La validazione vera la fa il server, e l'app mostra i suoi errori per campo. Le risposte sono tipizzate dal contratto generato. Un valore enum sconosciuto non manda in crash l'app: viene mostrato com'è.

**M5 — Insecure Communication.** *Parziale.* In produzione l'indirizzo delle API sarà HTTPS, con HSTS impostato dal backend. In sviluppo si usa HTTP verso `localhost`. Non c'è il certificate pinning: è un'aggiunta pesante da mantenere, e va valutata solo con un'app pubblicata.

**M6 — Inadequate Privacy Controls.** *Coperto.* L'app non registra dati nei log, non usa analytics e non chiede permessi del dispositivo. Al logout e al login svuota tutta la cache delle risposte. Un test controlla che, dopo un cambio di utente, i dati del primo non compaiano mai, nemmeno durante il caricamento.

**M7 — Insufficient Binary Protections.** *Accettato.* Nessuna offuscazione del codice. Il motivo è che nel bundle non c'è niente da proteggere: nessun segreto e nessuna logica di autorizzazione. Chi decompila l'app trova un client.

**M8 — Security Misconfiguration.** *Coperto.* Il login dice al sistema che i campi sono email e password (`textContentType`, `autoComplete`), così il gestore di password funziona e la password non finisce nei suggerimenti della tastiera. L'app non registra schemi di link per operazioni sensibili.

**M9 — Insecure Data Storage.** *Coperto su iOS e Android, con un limite sul web.* Il refresh token sta in `expo-secure-store`, cioè nel Keychain o nel Keystore. Il token di accesso sta solo in memoria. Le risposte non vengono salvate su disco. Sul web, usato solo per lo sviluppo, il refresh token finisce in `localStorage`: è scritto chiaramente nel codice.

**M10 — Insufficient Cryptography.** *Non applicabile.* L'app non fa crittografia propria. Si affida a TLS e al Keychain o Keystore del sistema.

**La sessione, in sintesi.** Un token rubato da un telefono vale poco. Il token di accesso dura 15 minuti. Il refresh token cambia a ogni rinnovo, e quello vecchio non funziona più. Il logout lo invalida sul server: lo ha verificato la prova end-to-end, in cui il vecchio token ha ricevuto 401.

## Alternative considerate

**Salvare tutto in AsyncStorage.** Più semplice, ma non è cifrato: chi ha accesso ai file dell'app legge il token.

**Certificate pinning subito.** Protegge da proxy che intercettano il traffico, ma un certificato rinnovato senza aggiornare l'app la blocca per tutti gli utenti. Sproporzionato per un'app non ancora pubblicata.

**Biometria per riaprire l'app.** Utile per un'app con dati di minori su telefoni condivisi, ma è una funzionalità nuova: fuori dalla fase di parità. È un buon candidato per la fase successiva.

## Errori comuni e trade-off

- **Credere che una chiave nel bundle sia nascosta.** Non lo è mai.
- **Controllare i permessi solo nell'app.** Chi chiama le API direttamente salta l'interfaccia.
- **Lasciare la cache dopo il logout.** Il prossimo utente vede i dati del precedente.
- **Ignorare `npm audit`**, oppure lanciarlo con `--force` senza pensarci. La strada giusta è capire cosa finisce nel bundle e cosa no.
- **Trade-off:** senza pinning e senza offuscazione, l'app si fida di TLS e del server. È coerente con un client senza segreti.

## Come lo spiegheresti a un colloquio

Alla fine della fase ho percorso la OWASP Mobile Top 10 e registrato un verdetto per ogni voce. L'app non contiene segreti: l'unica configurazione è l'indirizzo delle API, e tutta l'autorizzazione la decide il backend. Il refresh token sta nel Keychain o nel Keystore, il token di accesso solo in memoria, e il logout lo invalida anche sul server, come ha verificato la prova end-to-end. Al cambio di utente svuoto tutta la cache, con un test dedicato. Il punto aperto è la catena delle dipendenze: npm audit segnala vulnerabilità, quasi tutte negli strumenti di build, ma due in expo-router finiscono nel bundle, e le ho registrate come rischio accettato in attesa di una patch dell'SDK.

## Domande di autoverifica

1. **Perché nessun segreto può stare nel bundle?**
   Perché chiunque può scaricare l'app e leggerne il contenuto. Le variabili `EXPO_PUBLIC_*` finiscono nel codice distribuito.

2. **Dove sta il refresh token, e perché lì?**
   In `expo-secure-store`, cioè nel Keychain o nel Keystore, che il sistema cifra. Lo storage normale dell'app non è cifrato.

3. **Delle segnalazioni di `npm audit`, quali contano di più?**
   Quelle delle librerie che finiscono nel bundle, come `decode-uri-component` usata da `expo-router`. Quelle degli strumenti di build girano solo sul computer di chi sviluppa.

4. **Perché non usiamo `npm audit fix --force`?**
   Perché installerebbe versioni non allineate all'SDK di Expo, rischiando di rompere l'app.

5. **Cosa vale un token rubato dal telefono?**
   Poco: il token di accesso scade in 15 minuti, e il refresh token viene invalidato dal logout o dalla rotazione successiva.
