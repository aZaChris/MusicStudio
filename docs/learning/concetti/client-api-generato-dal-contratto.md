# Client API generato dal contratto

## TL;DR

Un'app che parla con un backend deve sapere che forma hanno i dati che riceve. Se quei tipi li scrivi a mano, prima o poi dicono una cosa e il server ne fa un'altra. In MusicStudio Mobile i tipi TypeScript sono generati dal contratto OpenAPI del backend Django. Uno script controlla che la copia del contratto nell'app sia uguale a quella del backend. Generarli ha fatto emergere tre errori nel contratto stesso.

## Il problema reale

L'app ereditata dal branch `app` aveva interfacce come questa, scritte a mano:

```ts
export interface Lesson {
  id: number;
  studentName: string;
  studentLastName: string;
  startTime: string;
}
```

Il backend Django invece risponde con `student_name` e `start_time`, e non ha un campo `studentLastName`. TypeScript non poteva saperlo: quei tipi erano una promessa che nessuno controllava. Il risultato sarebbe stato un'app che compila senza errori e mostra campi vuoti, o va in crash su un `undefined`.

È un problema generale. Il backend e l'app vivono in posti diversi, cambiano in momenti diversi e spesso li scrivono persone diverse. Se non c'è un documento condiviso e verificato che dice com'è fatta ogni risposta, prima o poi divergono.

## Come funziona

Pensa a un contratto d'affitto. Proprietario e inquilino non si fidano della memoria: c'è un documento firmato, e se qualcuno lo cambia, la nuova versione va firmata di nuovo. Il contratto OpenAPI è quel documento tra backend e app. Elenca ogni endpoint, ogni parametro e la forma esatta di ogni risposta.

Il backend di MusicStudio genera già il suo contratto dal codice, con drf-spectacular, e lo salva in `backend/openapi.yaml`. La CI del backend fallisce se il codice cambia senza aggiornare il file. Quindi il contratto è affidabile.

Da un contratto OpenAPI uno strumento come **openapi-typescript** genera i tipi TypeScript. Un campo segnato `readOnly` diventa `readonly`. Un campo che può essere `null` diventa `T | null`. Un enum diventa un'unione di stringhe, per esempio `"scheduled" | "completed" | "cancelled" | "no_show"`.

## Come lo abbiamo applicato in MusicStudio

**La copia del contratto.** L'app vive su un branch diverso dal backend, `refactor/mobile`. Il contratto quindi viene copiato in `contract/openapi.yaml`. Lo script `scripts/contract.mjs` lo legge con `git show` dal branch del backend:

```js
for (const ref of [BRANCH, `origin/${BRANCH}`]) {
  try {
    return execFileSync("git", ["show", `${ref}:${SOURCE}`], { encoding: "utf8" });
  } catch {
    // try the next ref
  }
}
```

Prima prova il branch locale, che può contenere correzioni non ancora pushate, poi quello remoto, l'unico disponibile in CI. L'ordine l'abbiamo invertito durante il lavoro: il primo tentativo prendeva `origin` e avrebbe copiato un contratto vecchio, senza le correzioni appena fatte.

**I tipi generati.** `npm run contract:sync` copia il contratto e rigenera `src/lib/api/schema.d.ts`. Il file è committato e non si modifica a mano. Il generatore gira con `npx openapi-typescript@7.13.0` invece che come dipendenza: chiede TypeScript 5, mentre il progetto usa la 6, e forzare l'installazione sarebbe stato peggio. Un file piccolo, `src/lib/api/types.ts`, dà nomi corti ai tipi che usiamo:

```ts
type Schemas = components["schemas"];
export type Lesson = Schemas["Lesson"];
export type Student = Schemas["Student"];
```

**Il controllo.** `npm run contract:check`, anche in CI, fallisce in due casi: se la copia è diversa da quella del backend, o se rigenerando i tipi si ottiene un file diverso da quello committato. L'abbiamo provato aggiungendo una riga al contratto: il controllo è fallito, come doveva.

**Il compilatore come lista dei lavori.** Appena le schermate hanno iniziato a usare i tipi generati, `tsc` ha elencato ogni punto da portare: `Property 'studentName' does not exist... Did you mean 'student_name'?`. Il porting è diventato una lista precisa invece di una caccia.

**Gli errori trovati nel contratto.** Generare i tipi ha fatto vedere cose che nessun client aveva mai controllato:

1. `GET /students/{id}/lessons/` era documentato come se restituisse uno `Student`, ma restituisce una lista di lezioni.
2. `active_package` di uno studente può essere `null`, ma il contratto diceva che c'è sempre. Il tipo generato avrebbe detto all'app che è impossibile non avere un pacchetto.
3. In `Me`, `teacher` e `parent_account` possono essere `null` (un genitore non ha un profilo insegnante), ma il contratto non lo diceva.

Tutti e tre sono stati corretti sul backend, con un test ciascuno, prima di andare avanti con l'app.

## Alternative considerate

**Tipi scritti a mano.** Veloci all'inizio, ed è proprio il problema che volevamo risolvere.

**orval o openapi-generator.** Generano un client completo, spesso con gli hook di React Query già pronti. Molto codice generato, difficile da leggere e da studiare. A noi servivano solo i tipi.

**openapi-fetch.** Una libreria minuscola che rende tipizzati anche i percorsi delle chiamate. Interessante, ma la gestione del refresh del token con un middleware è scomoda (vedi il documento sulla sessione).

**Un submodule git** per condividere il file. Pesante da gestire per un solo file.

## Errori comuni e trade-off

- **Fidarsi di un contratto non verificato.** I tipi generati sono affidabili solo quanto il contratto. Qui lo è perché la CI del backend lo confronta con il codice.
- **Modificare a mano il file generato.** Alla prossima sincronizzazione le modifiche spariscono, e il controllo fallisce.
- **Dimenticare `null`.** Un contratto che non dichiara i campi nullabili produce tipi troppo ottimisti. È l'errore più frequente, e ne abbiamo trovati tre.
- **Trade-off:** la copia del contratto va sincronizzata a mano quando il backend cambia. È voluto: un cambio di contratto deve essere una decisione visibile nel diff dell'app, non una sorpresa.

## Come lo spiegheresti a un colloquio

L'app non ha tipi scritti a mano per le risposte del server: li genero dal contratto OpenAPI del backend con openapi-typescript. Il contratto è copiato nel repository dell'app, e uno script in CI fallisce se la copia diverge dal backend o se i tipi non sono quelli generati. Quando le schermate sono passate ai tipi generati, il compilatore ha elencato ogni campo da cambiare, perché l'app usava camelCase e Django risponde in snake_case. Generare i tipi ha anche fatto emergere tre errori nel contratto, per esempio campi nullabili non dichiarati, che ho corretto sul backend con dei test. Così un cambio del backend si scopre in CI, non da un crash in produzione.

## Domande di autoverifica

1. **Perché i tipi scritti a mano sono un rischio?**
   Perché nessuno controlla che corrispondano al server. Possono compilare senza errori e descrivere campi che il server non manda.

2. **Cosa controlla `npm run contract:check`?**
   Che la copia del contratto sia uguale a quella del branch del backend, e che i tipi committati siano esattamente quelli che il generatore produce.

3. **Perché lo script legge prima il branch locale e poi `origin`?**
   Perché il branch locale può contenere correzioni al contratto non ancora pushate. In CI esiste solo `origin`.

4. **Che errore avrebbe causato `active_package` non dichiarato nullabile?**
   Il tipo avrebbe detto che il pacchetto c'è sempre, e l'app avrebbe letto i campi di un `null`, andando in crash per gli studenti senza pacchetto.

5. **Perché il generatore non è una dipendenza del progetto?**
   Perché richiede TypeScript 5 come peer, mentre il progetto usa la 6. Lanciarlo con `npx` a versione fissata evita il conflitto.
