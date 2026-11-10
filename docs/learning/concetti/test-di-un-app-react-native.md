# Testare un'app React Native: l'app vera e la rete finta

## TL;DR

L'app ereditata non aveva test. In MusicStudio Mobile ci sono 53 test con Jest e React Native Testing Library, più una verifica end-to-end della build web contro il backend Django vero. L'idea centrale: nei test gira l'app vera, con layout, autenticazione e schermate reali, e l'unica cosa finta è la rete. Così si prova il nostro codice, non i mock.

## Il problema reale

Senza test, ogni modifica all'app si verifica a mano: si apre, si clicca, si guarda. Non scala, e alcune cose a mano non si vedono proprio. Per esempio: cosa succede se tre richieste trovano il token scaduto nello stesso istante? O se un pagamento viene registrato a mezzanotte e mezza?

C'era anche un vincolo pratico: in questo ambiente di lavoro non ci sono emulatori iOS o Android. I test dovevano girare in Node, con Jest.

## Come funziona

Pensa a un simulatore di volo. Il pilota usa la cabina vera, gli strumenti veri e le procedure vere; finto è solo il mondo fuori dal finestrino. Se finti fossero anche gli strumenti, il simulatore non insegnerebbe niente.

Nei test di un'app vale la stessa idea. Ci sono due approcci:

- **mock dei moduli interni**: si sostituisce, per esempio, il client HTTP con un finto. Il test è facile, ma non prova il client: il rinnovo del token o la gestione degli errori non girano mai;
- **finto al confine**: si sostituisce solo `fetch`, cioè il punto in cui l'app esce verso la rete. Tutto il resto gira davvero.

React Native Testing Library (RNTL) aggiunge un principio: cercare gli elementi come li cerca un utente, per testo, etichetta di accessibilità e ruolo. Per esempio "il pulsante che si chiama Log in", non "il terzo componente".

## Come lo abbiamo applicato in MusicStudio

**Gli strumenti.** `jest-expo` come preset di Jest, RNTL 14, e `renderRouter` di Expo Router, che renderizza l'albero delle rotte vero:

```ts
export async function renderApp(initialUrl: string) {
  // RNTL 14's render is async: `screen` is only bound once it resolves.
  return await renderRouter("./src/app", { initialUrl });
}
```

**La rete finta.** `src/test/fake-api.ts` sostituisce `fetch` con un piccolo router. Ogni test dichiara le risposte:

```ts
await signedInAs(teacherMe, {
  "GET /dashboard/": { status: 200, body: dashboard() },
  "POST /lessons/1/complete/": { status: 409, body: { detail: "Lesson already completed." } },
});
```

Una risposta può essere anche una funzione, per esempio per rispondere 401 al token vecchio e 200 a quello nuovo. Il finto registra tutte le chiamate, quindi il test può controllare cosa è stato mandato, per esempio il corpo di un pagamento. `expo-secure-store` è sostituito da una mappa in memoria.

**Il fuso orario.** I test girano con `TZ=Europe/Rome`. Il test dei pagamenti finge solo l'orologio, alle 00:30 del 10 novembre, e controlla che la data mandata sia il 10 e non il 9 come darebbe l'ora UTC.

**I test che verificano i test.** Per tre comportamenti importanti abbiamo tolto il codice che li garantisce e controllato che il test fallisse: il rinnovo unico con tre richieste insieme, il secondo tentativo del logout, la pulizia della cache tra due utenti. Un test che passa anche senza il codice che dovrebbe proteggere non protegge niente.

**Le sorprese di RNTL 14.** In questa versione `render` e `fireEvent` sono asincroni. Senza `await`, `screen` non era ancora collegato ("render function has not been called"), e il form veniva inviato con i campi ancora vuoti, perché lo stato non era aggiornato. Le query `UNSAFE_*` sono state rimosse: per controllare il trentesimo studente di una lista virtualizzata, il test dà alla lista le dimensioni dello schermo e la fa scorrere come farebbe un utente.

**I tempi.** Con l'app intera in ogni test e sei processi in parallelo, su una macchina da 2,7 GB i limiti predefiniti non bastavano: 19 test fallivano in parallelo e passavano in sequenza. Il motivo erano i timeout, non il comportamento. Abbiamo alzato le attese a 5 secondi e il limite per test a 30.

**La verifica end-to-end.** I test con la rete finta non provano che app e backend vadano d'accordo: CORS, contratto, sessione vera. Per questo lo script `scripts/verify-django.mjs` usa Playwright sulla build web, contro Django e PostgreSQL veri. Per alcuni passi chiede conferma direttamente alle API: dopo il logout rimanda il vecchio refresh token e si aspetta 401. Risultato: 9 passi su 9, registrato in `docs/learning/verifica-end-to-end.md`.

## Alternative considerate

**Mock del client o degli hook.** Test più semplici, ma il codice più delicato, cioè sessione ed errori, non girerebbe mai.

**MSW (Mock Service Worker).** Lo standard per fingere la rete nel web. In React Native con Jest richiede polyfill, ed è una dipendenza in più per una dozzina di rotte.

**Detox o Maestro**, test end-to-end su emulatore. Ottimi, ma richiedono emulatori, che qui non ci sono.

**Snapshot dei componenti.** Si rompono a ogni cambio di stile e non dicono se il comportamento è giusto.

## Errori comuni e trade-off

- **Testare i mock.** Se il finto sta troppo all'interno, il test passa anche con il codice rotto.
- **Cercare per struttura** ("il secondo View") invece che per testo o ruolo: i test si rompono a ogni ritocco grafico.
- **Dimenticare `await`** con RNTL 14: errori strani e dati vuoti.
- **Non verificare che un test possa fallire.**
- **Trade-off:** renderizzare l'app intera rende i test più lenti, circa 40 secondi in tutto qui, ma molto più fedeli.

## Come lo spiegheresti a un colloquio

L'app non aveva test; ora ne ha 53 con Jest e React Native Testing Library. Nei test gira l'app vera, renderizzata con renderRouter di Expo Router, e l'unica cosa finta è fetch, sostituito da un piccolo router di risposte: così il rinnovo del token e la gestione degli errori girano davvero. Cerco gli elementi per ruolo ed etichetta di accessibilità, come farebbe un utente, e faccio girare i test nel fuso di Roma per trovare gli errori sulle date. Per i comportamenti più delicati ho verificato che i test falliscano togliendo il codice che li protegge. In più ho una verifica end-to-end con Playwright sulla build web contro il backend Django vero.

## Domande di autoverifica

1. **Perché fingiamo `fetch` invece del client HTTP?**
   Perché così il client gira davvero nei test, compresi il rinnovo del token e la trasformazione degli errori.

2. **Perché i test girano con `TZ=Europe/Rome`?**
   Per vedere gli errori sulle date come li vedrebbero gli utenti, per esempio la data UTC di ieri dopo mezzanotte.

3. **Come si controlla che un test sia utile?**
   Togliendo il codice che dovrebbe proteggere e verificando che il test fallisca.

4. **Cosa è cambiato in RNTL 14 rispetto alle versioni precedenti?**
   `render` e `fireEvent` sono asincroni e vanno aspettati; le query `UNSAFE_*` non esistono più.

5. **Cosa prova la verifica end-to-end che i test con Jest non provano?**
   Che app e backend vadano d'accordo davvero: CORS, contratto, sessione, e che il logout chiuda la sessione sul server.
