# ADR-040: Una policy di versionamento, la deprecazione con segnali e il controllo del contratto

- Stato: accettato
- Data: 2026-11-25

## Contesto

L'API vive sotto `/api/v1/` e la usano due client che non controlliamo del tutto: il portale web e l'app mobile. L'app si aggiorna dagli store, quindi lentamente: una versione vecchia resta installata per mesi. Finora nessun documento diceva che cosa promette "v1", come si annuncia una modifica che rompe i client, e per quanto tempo il comportamento vecchio resta in vita. La CI controllava solo che `openapi.yaml` fosse rigenerato, non che la modifica fosse compatibile.

## Decisione

- **Una policy scritta**, in inglese per gli sviluppatori dei client: `docs/operations/api-versioning-policy.md`. Elenca cosa è compatibile e cosa rompe, fissa un **preavviso minimo di 90 giorni** e spiega che un `v2` nasce solo con la prima modifica davvero incompatibile, accanto al `v1`.
- **Un decoratore `@deprecated`** in `apps/common/deprecation.py`. L'endpoint continua a rispondere uguale, e in più:
  - ogni risposta porta `Deprecation` nella forma dell'**RFC 9745** (`@` e i secondi Unix), `Sunset` (RFC 8594) e `Link` verso il successore e verso la policy;
  - il contratto lo segna `deprecated: true`, con la data di rimozione in testa alla descrizione;
  - ogni chiamata scrive una riga di log `deprecated_call` con endpoint e intestazione `X-Client`, senza dati della persona;
  - dalla data di rimozione risponde **410** con codice `endpoint_gone`, nella busta d'errore di sempre (`DomainError`).
- Un preavviso più corto di 90 giorni **fa fallire l'import**: non arriva mai a un deploy.
- **Un registro umano**, `docs/operations/deprecations.md`, e un rapporto di migrazione per ogni deprecazione (modello in `docs/operations/migrations/TEMPLATE.md`). La fonte di verità è il codice: un test fallisce se una deprecazione non ha la sua riga o il suo rapporto.
- **Un promemoria con scadenza**: il comando `deprecation_report` e il workflow settimanale `deprecation-watch.yml`, che diventa rosso a 30 giorni dalla rimozione. Non gira sulle pull request.
- **Un job di CI `contract-diff`** che confronta il contratto del branch con quello di `main` usando `oasdiff breaking` (versione fissata, checksum verificato). Una modifica incompatibile accettata richiede una riga in `.github/oasdiff-ignore.txt` con motivo e link alla PR.

## Alternative scartate

- **Creare subito un albero `v2`**: niente è ancora incompatibile, sarebbe codice speculativo.
- **`NamespaceVersioning` di DRF**: macchinario per una versione che non esiste.
- **`Deprecation: true`**: è la forma della bozza; l'RFC 9745 pubblicato nel 2025 usa una data strutturata. Abbiamo scelto la forma dello standard.
- **L'intestazione `Warning`**: obsoleta.
- **Un test con la data nella pipeline normale**: farebbe diventare rosse pull request che non c'entrano, solo perché è arrivato un giorno del calendario.
- **Un confronto del contratto scritto da noi**, oppure `openapi-diff` (serve Java): oasdiff capisce la semantica di OpenAPI, e un `diff` di testo no.
- **Solo un promemoria in calendario**: è personale e sta fuori dal repository.

## Conseguenze

- Prova reale, del 2026-11-25: con le regole predefinite oasdiff segnalava **13 errori** confrontando il contratto prima e dopo la fase 9, e nessuno era un vero problema. Erano 4 valori nuovi in un enum di risposta (le azioni del registro, una lista che cresce per natura) e 9 cambi di forma `allOf` dello stato dei pagamenti, con gli stessi valori accettati. Con `--flatten-allof` e il file `.github/oasdiff-levels.txt`, che trasforma "valore di enum aggiunto in risposta" in un avviso, il risultato è 0 errori. Rinominare `Lesson.start_time` in una copia di prova dà invece **10 errori** ed exit 1.
- Il prezzo di quella configurazione: un client che fa uno `switch` su un enum senza un ramo di default non è protetto dalla CI. Per questo la policy chiede ai client di gestire sempre i valori che non conoscono. È una scelta discutibile, e qui è scritta.
- Il numero di chiamate nel report è "unknown" finché i log JSON non stanno in un archivio interrogabile (`FUTURO (conteggio chiamate)`).
- In questa fase nessun endpoint vero è deprecato: il meccanismo è provato con una view di test.
