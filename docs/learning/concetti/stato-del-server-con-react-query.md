# Lo stato del server con React Query: errori, retry, invalidazione

## TL;DR

In un'app mobile quasi tutti i dati vengono dal server. React Query li carica, li tiene in cache e li ricarica quando servono. Ma va configurato: per default ritenta tre volte anche gli errori che non cambieranno mai. In MusicStudio Mobile ogni errore diventa un messaggio leggibile, i 4xx non vengono ritentati, ogni schermata mostra caricamento, errore e lista vuota allo stesso modo, e dopo ogni scrittura si invalida solo quello che è cambiato.

## Il problema reale

Nell'app ereditata gli errori sparivano. Se il server rifiutava un pagamento, il pulsante tornava normale e basta. Se la dashboard non caricava, la schermata restava vuota. L'utente non poteva sapere se aveva sbagliato qualcosa, se la rete era giù o se il server aveva un problema.

C'era anche un problema più sottile. React Query, per default, ritenta tre volte ogni richiesta fallita, con attese crescenti. Per un errore di rete ha senso. Ma un 403 ("non hai i permessi") o un 404 ("non esiste") non cambiano riprovando: tre tentativi ritardano solo il messaggio di qualche secondo, e fanno lavorare il server per niente.

## Come funziona

Pensa a un cameriere che porta le ordinazioni in cucina. Se la cucina dice "il piatto è finito", il cameriere non torna a chiedere tre volte: lo dice subito al cliente. Se invece la porta della cucina è bloccata, ha senso riprovare. La differenza sta nel tipo di risposta.

In HTTP la regola è semplice:

- **4xx**: la richiesta è sbagliata o non permessa. Riprovare non serve.
- **5xx o nessuna risposta**: il problema è del server o della rete. Riprovare può servire.

React Query ha anche l'**invalidazione**. Ogni dato in cache ha una chiave, per esempio `["dashboard"]` o `["students", 7]`. Dopo una scrittura si dichiarano "vecchie" le chiavi toccate, e React Query le ricarica. Invalidare `["students"]` invalida anche tutte le chiavi che iniziano così, come `["students", 7, "lessons"]`.

## Come lo abbiamo applicato in MusicStudio

**Un errore con dentro tutto.** Il client trasforma ogni risposta non riuscita in un `ApiError` con lo stato, il `detail` del server, il `code` e gli errori per campo di DRF. Lo stato 0 vuol dire "server non raggiungibile".

**Dall'errore al messaggio.** `src/lib/errors.ts` traduce l'errore nella lingua dell'utente:

```ts
switch (error.status) {
  case 0:   return t("error.network");
  case 401: return t("error.sessionExpired");
  case 403: return t("error.forbidden");
  case 404: return t("error.notFound");
  case 429: return t("error.rateLimited");
}
if (error.status >= 500) return t("error.server");
```

Per i 400 e i 409 mostra il motivo del server. Per esempio, completando una lezione già completata: "Il server ha rifiutato la richiesta: Lesson already completed.". Il testo del server è in inglese, perché il backend non traduce i suoi messaggi: è un limite dichiarato.

**La politica dei retry.** In `src/lib/query-client.ts`:

```ts
queries: { retry: (failures, error) => !isClientError(error) && failures < 2 },
mutations: { retry: false },
```

Nessun retry per i 4xx, al massimo due per rete e 5xx, e mai per le scritture: ritentare un pagamento da solo potrebbe registrarlo due volte. Un test controlla che un 403 produca una sola richiesta e un messaggio immediato.

**Un componente per tutti gli stati.** `QueryState` riceve la query e decide cosa mostrare: un indicatore di caricamento, l'errore con un pulsante "Riprova", un testo per la lista vuota, oppure il contenuto. Ogni schermata lo usa, quindi nessuna può più restare vuota in silenzio. Ogni schermata ha test per tutti e quattro gli stati.

**Gli errori nei form.** Nei form il messaggio compare accanto al pulsante, e quello che l'utente ha scritto resta. Se il server rifiuta un importo, l'importo non sparisce. La finestra per completare una lezione resta aperta se il server dice di no.

**L'invalidazione dopo le scritture.** Completare una lezione invalida `["dashboard"]` e `["students"]`: cambiano le prossime lezioni e le lezioni rimaste nel pacchetto. Registrare un pagamento invalida anche `["payments"]`. Al logout invece si svuota tutto con `queryClient.clear()`.

**Tutte le pagine.** Django restituisce le liste a pagine da 25. L'app ereditata mostrava solo la prima pagina. Ora `fetchAllPages` segue il link `next` fino in fondo. Il link è assoluto e contiene il nome host che il server ha visto: lo usiamo solo per il percorso e la query, e parliamo sempre con l'indirizzo configurato. È un limite consapevole, scritto nel codice: per 1–10 insegnanti le liste sono corte, e se crescessero si passerebbe allo scroll infinito.

**Un QueryClient per montaggio.** Prima il client era creato a livello di modulo, uno solo per tutta la vita del processo. Ora nasce dentro il layout radice con `useState`. Ogni test ne ha uno nuovo, e il logout può svuotarlo senza effetti collaterali.

## Alternative considerate

**Gestire gli errori schermata per schermata.** È così che erano nati i silenzi dell'app ereditata: ogni schermata li gestiva a modo suo, o non li gestiva.

**Un error boundary globale.** Utile per i crash, ma non per un 409 in un form: lì il messaggio deve stare vicino al pulsante.

**Lo scroll infinito subito** con `useInfiniteQuery`. Più codice e più stati da testare, per liste che oggi sono corte.

## Errori comuni e trade-off

- **Lasciare i retry predefiniti.** Un 403 si vede dopo secondi, e il server riceve tre richieste inutili.
- **Ritentare le scritture.** Rischio di duplicati, a meno che il server non usi una chiave di idempotenza.
- **Invalidare tutto dopo ogni scrittura.** Funziona, ma ricarica dati che non sono cambiati.
- **Non svuotare la cache al logout.** Il prossimo utente vede i dati di quello prima.
- **Trade-off:** caricare tutte le pagine all'inizio rende la prima apertura più lenta per uno studio grande. Per 300 studenti sono 12 richieste.

## Come lo spiegheresti a un colloquio

Uso React Query per lo stato del server, ma configurato: nessun retry per i 4xx, perché un 403 o un 409 non cambiano riprovando, al massimo due per rete e 5xx, e mai per le scritture. Il client trasforma ogni risposta non riuscita in un errore tipizzato, e una funzione lo traduce in un messaggio nella lingua dell'utente, con il motivo del server per i conflitti. Un componente unico gestisce caricamento, errore, lista vuota e contenuto, quindi nessuna schermata resta vuota in silenzio. Dopo ogni scrittura invalido solo le chiavi toccate, e al logout svuoto tutta la cache. Le liste paginate di Django le carico per intero, un limite che ho scritto nel codice insieme alla strada per superarlo.

## Domande di autoverifica

1. **Perché non ritentiamo i 4xx?**
   Perché sono errori della richiesta: permessi, dati non validi, risorse inesistenti. Riprovare non li cambia e ritarda solo il messaggio.

2. **Perché le scritture non vengono mai ritentate in automatico?**
   Perché un retry di un pagamento potrebbe registrarlo due volte.

3. **Cosa succede alla cache dopo il completamento di una lezione?**
   Vengono invalidate la dashboard e gli studenti, che React Query ricarica.

4. **A cosa serve `QueryState`?**
   A mostrare in modo uniforme caricamento, errore con "Riprova", lista vuota e contenuto, così nessuna schermata resta vuota senza spiegazione.

5. **Perché il link `next` di Django non viene usato così com'è?**
   Perché contiene il nome host visto dal server, che può essere diverso da quello configurato nell'app. Usiamo solo percorso e query.
