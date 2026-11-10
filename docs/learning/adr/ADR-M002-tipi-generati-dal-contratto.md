# ADR-M002: Tipi TypeScript generati dal contratto OpenAPI del backend

- Stato: accettato
- Data: 2026-11-09

## Contesto

L'app ereditata aveva i tipi delle risposte scritti a mano, in camelCase (`studentName`, `lessonsRemaining`). Django risponde in snake_case (`student_name`, `lessons_remaining`). Scritti a mano, i tipi possono dire una cosa e il server farne un'altra, e il compilatore non se ne accorge. Il backend ha già un contratto OpenAPI versionato e controllato dalla CI (`backend/openapi.yaml`).

## Decisione

- Una copia del contratto sta in `contract/openapi.yaml`.
- `openapi-typescript@7.13.0` genera `src/lib/api/schema.d.ts`, che si committa e non si modifica a mano. `src/lib/api/types.ts` dà nomi corti ai tipi che servono.
- `scripts/contract.mjs sync` aggiorna copia e tipi dal branch del backend: prima quello locale, che può avere correzioni non ancora pushate, poi `origin`.
- `scripts/contract.mjs check`, anche in CI, fallisce se la copia è diversa dal backend o se i tipi non sono quelli che il generatore produce.
- Il generatore gira con `npx` a versione fissata, non come dipendenza del progetto: chiede TypeScript 5 come peer, e il progetto usa la 6.

## Alternative scartate

- **Tipi scritti a mano**: è il problema che stiamo risolvendo.
- **orval o openapi-generator**: generano client e hook completi, molto più codice di quello che serve.
- **Un submodule git**: pesante per un solo file.

## Conseguenze

- Il passaggio ai tipi generati ha fatto elencare al compilatore ogni punto delle schermate da portare.
- Generarli ha fatto emergere tre errori nel contratto del backend: un'azione documentata con il tipo sbagliato e tre campi che possono essere `null` ma non lo dicevano. Sono stati corretti sul backend, con test.
- Quando il backend cambia il contratto, l'app lo scopre in CI invece che da un crash.
