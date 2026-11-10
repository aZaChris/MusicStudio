# Domande da colloquio: l'app mobile

Ogni domanda ha una risposta modello e il punto debole da dire prima che te lo chiedano. Le domande sul backend sono nel documento del branch `refactor/production-standards`.

## Architettura

### 1. Com'è fatta l'app mobile?

**Risposta modello.** È un'app Expo con Expo Router, React Query e TypeScript in modalità strict. Le schermate stanno in `src/app`, divise tra area insegnante e portale genitore. Tutto quello che sa di HTTP e del contratto è in `src/lib/api`: un client piccolo scritto da noi e i tipi generati dal contratto OpenAPI del backend Django. Le schermate usano solo hook.

**Punto debole.** Il client carica tutte le pagine delle liste all'inizio. Va bene per uno studio di musica, non per migliaia di elementi.

### 2. Perché hai rifatto l'app invece di scriverne una nuova?

**Risposta modello.** Perché l'interfaccia funzionava: rotte, tema, traduzioni, componenti. Era sbagliato lo strato dati, scritto per un altro backend. Ho fatto come per il backend: un audit del punto di partenza, poi un refactor documentato, con il vecchio branch lasciato intatto per il confronto.

**Punto debole.** Ho ereditato anche scelte che non avrei fatto, come le icone delle tab fatte con caratteri di testo. Le ho tenute per restare a parità di funzioni.

## Contratto e tipi

### 3. Come eviti che app e backend divergano?

**Risposta modello.** I tipi non li scrivo a mano: li genero dal contratto OpenAPI del backend con openapi-typescript. Il contratto è copiato nell'app, e uno script in CI fallisce se la copia è diversa da quella del backend o se i tipi non sono quelli generati.

**Punto debole.** Il contratto va sincronizzato a mano quando il backend cambia. È voluto, perché il cambio si vede nel diff, ma è un passaggio in più.

### 4. Generare i tipi ti ha fatto scoprire qualcosa?

**Risposta modello.** Tre errori nel contratto del backend: un endpoint documentato con il tipo di risposta sbagliato, e campi che possono essere `null` ma non lo dichiaravano. Li ho corretti sul backend con dei test prima di andare avanti. Senza la correzione l'app avrebbe letto campi di un `null`.

**Punto debole.** Nessun client generato aveva mai usato quel contratto: un contratto non consumato da nessuno può essere sbagliato senza che nessuno se ne accorga.

## Sessione e sicurezza

### 5. Come gestisci il rinnovo del token?

**Risposta modello.** Il token di accesso sta in memoria, il refresh token nel Keychain o nel Keystore. Su un 401 rinnovo e riprovo una volta. Le richieste che scadono insieme condividono una sola promise di rinnovo, perché il backend mette nella lista nera il refresh usato: un secondo rinnovo in parallelo verrebbe rifiutato e disconnetterebbe l'utente.

**Punto debole.** Sul web, che uso solo per lo sviluppo, il refresh token sta in `localStorage`.

### 6. Il logout è solo locale?

**Risposta modello.** No: chiama il backend, che mette il refresh token nella lista nera, poi cancella comunque i dati locali e svuota la cache. La verifica end-to-end lo conferma: il vecchio token, rimandato al server, riceve 401. Ho anche trovato un caso sottile: con il token di accesso scaduto, il rinnovo ruotava il refresh token prima del logout, e il corpo della richiesta conteneva quello vecchio. Ora rileggo il token e riprovo una volta.

**Punto debole.** Se il server non è raggiungibile al momento del logout, il refresh token resta valido sul server fino alla scadenza.

### 7. Come eviti che un secondo utente veda i dati del primo?

**Risposta modello.** Svuoto tutta la cache di React Query al logout e al login, e all'avvio chiedo al server chi è l'utente invece di fidarmi di un dato salvato. Un test fa logout, login con un altro utente, e controlla che i numeri del primo non compaiano mai, nemmeno durante il caricamento.

**Punto debole.** Il test copre la cache delle risposte; i dati nello stato locale delle schermate si azzerano perché le schermate si smontano al logout.

## Errori e dati

### 8. Come gestisci gli errori del server?

**Risposta modello.** Ogni risposta non riuscita diventa un errore tipizzato, tradotto in un messaggio nella lingua dell'utente; per i conflitti mostro il motivo del server. React Query non ritenta i 4xx, perché non cambiano, e non ritenta mai le scritture, per non registrare due volte un pagamento.

**Punto debole.** I messaggi del server sono in inglese, perché il backend non li traduce.

### 9. Hai trovato bug sulle date?

**Risposta modello.** Sì. L'app ereditata datava i pagamenti con la parte iniziale di `toISOString()`, cioè la data UTC: dopo mezzanotte in Italia era ancora ieri. Ora uso la data locale, e i test girano nel fuso di Roma con l'orologio fermo alle 00:30.

**Punto debole.** Anche il parsing delle date senza orario è delicato: `new Date("2026-11-09")` è la mezzanotte UTC. Le leggo come date locali apposta.

## Test

### 10. Come testi un'app React Native senza emulatori?

**Risposta modello.** Con Jest e React Native Testing Library renderizzo l'app vera, con renderRouter di Expo Router, e fingo solo fetch. Così sessione ed errori girano davvero. Cerco gli elementi per ruolo ed etichetta, come un utente. In più ho una verifica end-to-end con Playwright sulla build web contro il backend Django vero: 9 passi su 9.

**Punto debole.** Non ho provato l'app su un telefono vero: Keychain, Keystore e il comportamento nativo li verificherà il proprietario con Expo Go.

### 11. Come sai che i tuoi test servono?

**Risposta modello.** Per i comportamenti più delicati ho tolto il codice che li protegge e controllato che il test fallisse: il rinnovo unico, il secondo tentativo del logout, la pulizia della cache. Un test che passa anche senza il codice non protegge niente.

**Punto debole.** Non l'ho fatto per tutti i test, solo per quelli più critici.

## Domanda finale tipica

### 12. Cosa faresti adesso?

**Risposta modello.** Proverei l'app su un telefono vero con Expo Go, aggiornerei expo-router quando una patch dell'SDK chiude le vulnerabilità che finiscono nel bundle, e valuterei lo sblocco con biometria per i telefoni condivisi tra genitori e figli.

**Punto debole.** Nessuno: è una domanda che premia l'onestà sui limiti.
