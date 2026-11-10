# Glossario dell'app mobile

Ogni termine è in inglese, come lo troverai nel codice e nei colloqui, con una spiegazione in italiano semplice. In ordine alfabetico. I termini del backend sono nel glossario del branch `refactor/production-standards`.

**Access token (token di accesso).** Il token che accompagna ogni richiesta alle API. In MusicStudio dura 15 minuti e l'app lo tiene solo in memoria.

**ApiError.** La classe con cui il nostro client rappresenta una risposta non riuscita: stato HTTP, messaggio del server, codice ed errori per campo. Stato 0 vuol dire server non raggiungibile.

**Bundle.** Il codice JavaScript dell'app impacchettato e distribuito sui telefoni. Tutto quello che contiene va considerato pubblico.

**Cache invalidation (invalidazione).** Dichiarare "vecchio" un dato in cache, così React Query lo ricarica. Si fa dopo ogni scrittura, sulle chiavi toccate.

**Contract (contratto OpenAPI).** Il documento che descrive endpoint, parametri e forma delle risposte del backend. L'app ne tiene una copia in `contract/openapi.yaml` e ne genera i tipi.

**Expo.** La piattaforma sopra React Native che dà strumenti, librerie native pronte e l'app Expo Go per provare senza compilare.

**Expo Go.** L'app per telefono che esegue un progetto Expo senza una build nativa personalizzata. La constitution chiede che MusicStudio Mobile ci giri sempre.

**Expo Router.** Il sistema di navigazione di Expo basato sui file: ogni file in `src/app/` è una schermata.

**expo-secure-store.** La libreria che salva valori nel Keychain di iOS o nel Keystore di Android, spazi cifrati dal sistema. Ci teniamo il refresh token.

**Fake API (rete finta).** Nei test, la sostituzione di `fetch` con risposte dichiarate dal test. Tutto il resto dell'app gira davvero.

**jest-expo.** Il preset di Jest che configura l'ambiente per testare un progetto Expo.

**Keychain / Keystore.** Gli archivi cifrati di iOS e Android per credenziali e chiavi.

**openapi-typescript.** Lo strumento che genera i tipi TypeScript da un contratto OpenAPI.

**Pagination (paginazione).** Restituire una lista a pezzi. Django manda pagine da 25 elementi con un link `next` alla pagina successiva.

**Playwright.** Uno strumento che guida un browser vero da uno script. Lo usiamo per la verifica end-to-end della build web.

**Query key.** La chiave con cui React Query identifica un dato in cache, per esempio `["students", 7]`.

**QueryState.** Il nostro componente che mostra in modo uniforme caricamento, errore, lista vuota o contenuto.

**React Native Testing Library (RNTL).** La libreria per testare componenti React Native cercando gli elementi come farebbe un utente: per testo, ruolo ed etichetta.

**React Query (TanStack Query).** La libreria che carica i dati dal server, li tiene in cache e li ricarica quando servono.

**Refresh token.** Il token che serve solo a ottenere un nuovo token di accesso. Dura 14 giorni e cambia a ogni rinnovo.

**renderRouter.** La funzione di Expo Router per i test che renderizza l'albero delle rotte vero a partire da un URL.

**Retry policy (politica dei retry).** Le regole su quando riprovare una richiesta fallita. Da noi: mai per i 4xx e per le scritture, al massimo due volte per rete e 5xx.

**Single flight.** Fare un'operazione una sola volta anche se più chiamanti la chiedono insieme: il primo la avvia, gli altri aspettano lo stesso risultato. Lo usiamo per il rinnovo del token.

**Token rotation (rotazione).** A ogni rinnovo il server dà un refresh token nuovo e mette il vecchio nella lista nera.

**Vendoring.** Copiare nel proprio repository un file o una libreria esterna, invece di scaricarla ogni volta. Lo facciamo con il contratto del backend.

**Virtualized list (lista virtualizzata).** Una lista, come `FlatList`, che disegna solo gli elementi visibili. Nei test bisogna farla scorrere per vedere gli altri.
