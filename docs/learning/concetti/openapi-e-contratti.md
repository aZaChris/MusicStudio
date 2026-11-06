# OpenAPI e contratti API

## TL;DR

Un contratto API è la descrizione precisa di cosa un'API accetta e restituisce, compresi gli errori. OpenAPI è il formato standard per scriverlo. In MusicStudio lo schema OpenAPI è generato dal codice con drf-spectacular, salvato nel repository e controllato in CI. Ogni operazione ha il suo dominio e documenta gli errori che un client deve gestire. Se il codice cambia il contratto senza aggiornare il file, la pipeline fallisce.

## Il problema reale

Un'API ha dei clienti: in MusicStudio una SPA web e, in futuro, un'app mobile. Questi client sono scritti da persone che non leggono il codice Django. Si basano su una descrizione.

Se la descrizione esiste solo "a runtime", cioè la vedi aprendo `/api/docs/` sul server, nessuno nota quando cambia. Uno sviluppatore rinomina un campo in un serializer. La revisione del codice guarda il Python, non il contratto. Il giorno dopo l'app mobile si rompe.

C'era anche un secondo problema: gli errori non erano documentati. Un client deve sapere che una prenotazione può fallire con 409 se l'orario è occupato, o con 429 se fa troppe richieste. Senza documentazione lo scopre in produzione.

## Come funziona

Pensa al contratto d'affitto di un appartamento. Dice cosa è incluso, quanto si paga e cosa succede se qualcosa va storto. Né il proprietario né l'inquilino possono cambiarlo da soli senza che l'altro se ne accorga: ogni modifica è scritta, firmata e visibile. Un contratto API è lo stesso, tra il backend e i suoi client.

**OpenAPI** è un formato YAML o JSON che descrive un'API: i percorsi, i metodi, i parametri, la forma dei dati in ingresso e in uscita, le risposte possibili. Da un file OpenAPI si possono generare documentazione interattiva (Swagger UI), client in vari linguaggi e test.

Ci sono due approcci per mantenerlo.

**Contract-first.** Si scrive prima il file OpenAPI, lo si concorda con chi usa l'API, e poi si scrive il codice che lo rispetta. È tipico di organizzazioni grandi con molti team.

**Code-first.** Il codice è la fonte. Lo schema viene generato dal codice. Il rischio è che cambi senza che nessuno lo noti. La soluzione è **salvare lo schema generato nel repository** e controllare che sia sempre aggiornato. Così ogni modifica al contratto appare nel diff della pull request, e qualcuno la vede.

In Django REST Framework lo strumento più usato per generare lo schema è **drf-spectacular**. Legge viste, serializer e permessi e produce un file OpenAPI 3. Si personalizza con un `AutoSchema` e con dei "postprocessing hook", funzioni che modificano lo schema finale.

## Come lo abbiamo applicato in MusicStudio

Il file è `backend/openapi.yaml`, circa 2.600 righe, generato con:

```bash
uv run python manage.py spectacular --settings=config.settings.test --file openapi.yaml
```

**Tre controlli lo tengono aggiornato.** Il test `backend/config/tests/test_schema.py` rigenera lo schema e lo confronta con il file salvato: se differiscono, fallisce e stampa il comando da lanciare. Lo step "OpenAPI contract is committed and up to date" in `.github/workflows/ci.yml` fa lo stesso con un `diff`. Un hook pre-commit rigenera il file prima di ogni commit.

**I tag per dominio.** In `backend/apps/common/schema.py`, `MusicStudioAutoSchema.get_tags()` legge il modulo della vista (per esempio `apps.lessons.views`) e usa il nome dell'app come tag. Nella documentazione le operazioni sono raggruppate in accounts, studios, students, packages, lessons e payments, con una descrizione per ognuno nelle impostazioni.

**Gli errori documentati.** Invece di scrivere `@extend_schema(responses=...)` su ogni vista, un solo postprocessing hook, `add_error_responses`, aggiunge due schemi comuni e le risposte giuste a ogni operazione:

```python
if method in ("post", "put", "patch"):
    responses.setdefault("400", _json("Invalid input.", VALIDATION_REF))
if needs_auth:
    responses.setdefault("401", _json("Missing or invalid token.", ERROR_REF))
    responses.setdefault("403", _json("Role or object not allowed.", ERROR_REF))
if "{" in path:
    responses.setdefault("404", _json("Not found or outside your studio.", ERROR_REF))
```

Il 409 compare solo sulle scritture delle lezioni, non sull'annullamento, che libera lo spazio. Il 429 compare ovunque, per il rate limiting.

**Richiesta e risposta separate.** Con `COMPONENT_SPLIT_REQUEST` ogni serializer produce due schemi, uno per l'input e uno per l'output. Così campi in sola lettura come `teacher` o `end_time` non sembrano obbligatori quando si crea una lezione.

**Il prima e dopo.** Prima: schema solo a runtime, tag automatici dal percorso, nessun errore documentato. Dopo: un file nel repository revisionato a ogni modifica, operazioni raggruppate per dominio, e per ognuna gli errori con la loro forma.

## Alternative considerate

**Decoratori su ogni vista.** Più precisi, ma ripetitivi. Su una vista nuova è facile dimenticarli, e la documentazione diventa incoerente.

**Schema solo a runtime.** È quello che avevamo. Nessuna revisione dei cambi di contratto.

**Contract-first.** Più rigoroso, ma con un solo team e un solo backend raddoppia il lavoro.

**Test di contratto con un client generato.** Generare un client dallo schema e usarlo nei test. Molto robusto, ma più complesso. Può arrivare in una fase successiva.

## Errori comuni e trade-off

- **Schema salvato ma non controllato.** Diventa vecchio in pochi giorni e mente ai client.
- **Hook che riformattano il file generato.** Un hook che toglie spazi finali modificherebbe lo schema, e il confronto fallirebbe sempre. Per questo `backend/openapi.yaml` è escluso dagli hook di pulizia.
- **Documentare errori che non possono capitare.** Confonde i client. Per questo il 409 non è sull'annullamento.
- **Rompere il contratto senza versionarlo.** Un campo rimosso o rinominato rompe i client esistenti. La politica di versione e deprecazione è nel piano della fase 5.
- **Trade-off:** le regole del hook sono euristiche, basate su metodo e percorso. Se aggiungiamo un nuovo tipo di conflitto, va aggiornato anche il hook.

## Come lo spiegheresti a un colloquio

L'API ha due client, quindi tratto lo schema OpenAPI come un contratto. È generato dal codice con drf-spectacular, ma è salvato nel repository, e un test, la CI e un hook pre-commit falliscono se non è aggiornato. Così ogni cambio di contratto compare nel diff della pull request e viene revisionato. Le operazioni sono raggruppate per dominio, e un postprocessing hook documenta in un punto solo gli errori che ogni client deve gestire, compresi 409 per gli orari occupati e 429 per il rate limiting. Ho scelto code-first con lo schema controllato invece di contract-first perché c'è un solo team e un solo backend.

## Domande di autoverifica

1. **Che differenza c'è tra contract-first e code-first?**
   Nel contract-first si scrive prima lo schema e poi il codice. Nel code-first lo schema è generato dal codice.

2. **Perché salvare nel repository uno schema che si può generare?**
   Perché così ogni modifica al contratto appare nel diff della pull request e viene vista in revisione.

3. **Cosa fa il postprocessing hook `add_error_responses`?**
   Aggiunge gli schemi comuni degli errori e le risposte 400, 401, 403, 404, 409 e 429 alle operazioni dove possono capitare.

4. **A cosa serve `COMPONENT_SPLIT_REQUEST`?**
   A separare lo schema di input da quello di output, così i campi in sola lettura non sembrano obbligatori nelle richieste.

5. **Perché `openapi.yaml` è escluso dagli hook di pulizia di pre-commit?**
   Perché modificherebbero il file generato, e il confronto con lo schema rigenerato fallirebbe sempre.
