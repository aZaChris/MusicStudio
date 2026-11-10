# La sessione JWT nel client: rinnovo, rotazione e logout

## TL;DR

Il backend dà due token: uno di accesso che dura 15 minuti e un refresh token che dura 14 giorni e cambia a ogni rinnovo. L'app deve rinnovare in silenzio, senza mai fare due rinnovi insieme, e il logout deve chiudere la sessione anche sul server. In MusicStudio Mobile il token di accesso sta in memoria, il refresh token nel Keychain o nel Keystore, e un'unica promise condivisa serve tutte le richieste che trovano il token scaduto.

## Il problema reale

L'app ereditata salvava un solo token e non lo rinnovava mai. Contro il backend Django, dopo 15 minuti ogni chiamata avrebbe risposto 401 e l'app sarebbe rimasta su schermate vuote. Il logout cancellava il token dal telefono, ma il server non ne sapeva niente.

Il backend, nella fase 4, ha reso i refresh token revocabili. A ogni rinnovo il refresh usato finisce nella lista nera. Questo protegge da chi ruba un token, ma impone una regola al client: **mai due rinnovi in parallelo con lo stesso refresh token**. Il secondo verrebbe rifiutato, perché il primo lo ha appena bruciato, e l'utente si ritroverebbe disconnesso senza motivo.

Succede più spesso di quanto sembri. All'apertura della home partono insieme la dashboard, gli studenti e i pagamenti. Se il token è scaduto, ricevono 401 tutte e tre nello stesso istante.

## Come funziona

Pensa a una biblioteca che dà un pass giornaliero e una tessera annuale. Con il pass entri nelle sale. Quando scade, vai allo sportello con la tessera, ti danno un pass nuovo e una tessera nuova, e quella vecchia viene annullata. Se tre persone della stessa famiglia vanno allo sportello con la stessa tessera, solo la prima riceve il pass nuovo; le altre trovano la tessera già annullata.

La soluzione è mandare una persona sola allo sportello, e far aspettare le altre. In programmazione si chiama **single flight**: la prima richiesta che ha bisogno del rinnovo lo avvia e salva la promise; quelle che arrivano mentre il rinnovo è in corso aspettano la stessa promise invece di avviarne un'altra.

Altri due concetti:

- **Dove salvare i token.** Su iOS e Android esiste uno spazio cifrato del sistema: Keychain e Keystore. `expo-secure-store` lo usa. Lo storage normale dell'app non è adatto a un token che vale 14 giorni.
- **Il logout lato server.** Cancellare il token dal telefono non basta: chi ne ha una copia può ancora usarlo. Bisogna dire al server di metterlo nella lista nera.

## Come lo abbiamo applicato in MusicStudio

Tutto sta in `src/lib/api/client.ts`.

**Dove stanno i token.** Il token di accesso è una variabile in memoria: dura 15 minuti e non serve salvarlo. Il refresh token va in `expo-secure-store`. Sul web, usato solo per lo sviluppo, finisce in `localStorage`, ed è scritto chiaramente nel codice.

**Il single flight.** È una riga:

```ts
let refreshing: Promise<string | null> | null = null;

export function refreshAccess(): Promise<string | null> {
  refreshing ??= doRefresh().finally(() => {
    refreshing = null;
  });
  return refreshing;
}
```

Se un rinnovo è già in corso, `??=` non ne avvia un altro e restituisce quello esistente. Quando finisce, la variabile torna `null`.

**Il flusso di una richiesta.** `apiFetch` manda la richiesta con il token di accesso. Se riceve 401, chiama `refreshAccess()` e riprova una volta. Se il rinnovo viene rifiutato, cancella la sessione e avvisa il contesto di autenticazione, che porta l'utente al login con il messaggio "La sessione è terminata". Se invece il server non è raggiungibile, il rinnovo lancia un errore di rete e la sessione resta: essere offline non deve disconnettere nessuno.

**La prova.** Un test manda tre richieste con un token scaduto e si aspetta un solo rinnovo. Abbiamo verificato che il test sia utile: togliendo il `??=` fallisce, con tre rinnovi tutti con lo stesso refresh token.

**L'avvio.** L'app non si fida di un utente salvato. Se trova un refresh token chiede `GET /auth/me/`. Se il server risponde, sa chi sei e con quale ruolo. Se non risponde perché sei offline, mostra "Impossibile raggiungere il server" con un pulsante Riprova, senza disconnetterti.

**Il logout, e un caso sottile.** Il logout manda il refresh token a `POST /auth/logout/`, poi cancella il token e tutta la cache delle risposte. Ma c'era un caso nascosto. Se il token di accesso è scaduto, la chiamata di logout prima riceve 401 e fa un rinnovo, che ruota il refresh token. Il corpo della chiamata però contiene ancora quello vecchio, appena messo nella lista nera: il server risponde 400, e il refresh token nuovo resta valido. La correzione: se il primo tentativo fallisce con 400, rileggiamo il token e riproviamo una volta. Un test lo copre, e fallisce se si toglie il secondo tentativo.

**Niente dati del vecchio utente.** Al logout e al login la cache di React Query viene svuotata. Un test fa logout, login con un secondo utente, e controlla che durante il caricamento i numeri del primo utente non compaiano mai.

## Alternative considerate

**Un interceptor di axios o un middleware di openapi-fetch.** Funzionano, ma aggiungono una dipendenza, e rimandare una richiesta da un middleware, quando il corpo è già stato letto, è scomodo.

**Rinnovare in anticipo con un timer**, prima della scadenza. Evita alcuni 401, ma serve comunque la gestione del 401, per esempio dopo che il telefono è rimasto in tasca per un'ora. Più codice per lo stesso risultato.

**Salvare anche il token di accesso.** Nessun vantaggio: dura 15 minuti, e all'avvio un rinnovo serve comunque.

## Errori comuni e trade-off

- **Rinnovi paralleli** con token a rotazione: disconnessioni casuali, difficilissime da riprodurre.
- **Logout solo locale**: il token resta valido sul server.
- **Disconnettere chi è offline**: l'utente perde la sessione per un tunnel in metropolitana.
- **Ritentare all'infinito**: dopo un rinnovo riuscito, un secondo 401 vuol dire che l'account non è più valido, e lì ci si ferma.
- **Trade-off:** sul web il refresh token sta in `localStorage`, leggibile da qualunque script della pagina. Va bene solo perché la build web serve allo sviluppo.

## Come lo spiegheresti a un colloquio

Il backend usa un token di accesso di 15 minuti e un refresh token con rotazione e lista nera. Nell'app tengo il token di accesso in memoria e il refresh token nel Keychain o nel Keystore con expo-secure-store. Su un 401 rinnovo e riprovo una volta, e le richieste che scadono insieme condividono un'unica promise di rinnovo, perché un secondo rinnovo con lo stesso token verrebbe rifiutato dal server. Il logout chiama il server e svuota la cache, così il prossimo utente non vede niente del precedente. Ho anche trovato e coperto con un test il caso del logout con token scaduto, in cui la rotazione rendeva vecchio il token nel corpo della richiesta.

## Domande di autoverifica

1. **Perché due rinnovi in parallelo sono un problema con questo backend?**
   Perché a ogni rinnovo il refresh token usato finisce nella lista nera. Il secondo rinnovo userebbe un token appena bruciato e verrebbe rifiutato.

2. **Come funziona il single flight nel nostro client?**
   La prima richiesta avvia il rinnovo e ne salva la promise; le altre, finché il rinnovo è in corso, aspettano la stessa promise.

3. **Cosa succede se il server non è raggiungibile durante un rinnovo?**
   L'errore è di rete, stato 0. La sessione resta, e l'utente vede un messaggio di connessione invece di essere disconnesso.

4. **Perché il primo tentativo di logout poteva fallire?**
   Perché il token di accesso era scaduto: il rinnovo ruotava il refresh token, ma il corpo della chiamata conteneva ancora quello vecchio, già nella lista nera.

5. **Perché svuotiamo la cache al login e al logout?**
   Per non mostrare mai i dati di un utente a quello successivo, nemmeno per un istante durante il caricamento.
