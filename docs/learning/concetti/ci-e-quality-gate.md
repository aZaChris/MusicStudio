# CI e quality gate

## TL;DR

La CI (continuous integration) è un sistema che, a ogni push, scarica il codice e lo controlla in automatico. Il quality gate è la regola "se un controllo fallisce, il codice non entra". In MusicStudio GitHub Actions esegue sette controlli: lint, formattazione, tipi, migrazioni, test con copertura, contro un PostgreSQL e un Redis veri, più lo schema OpenAPI. Gli stessi controlli veloci girano in locale prima di ogni commit con pre-commit.

## Il problema reale

All'inizio di questo lavoro MusicStudio aveva ruff configurato e 26 test. Ma non c'era nessun sistema che li eseguisse. Funzionavano solo se qualcuno si ricordava di lanciarli. E prima o poi qualcuno se ne dimentica. Magari di venerdì sera, con una correzione "piccola".

Le regole scritte in un documento si erodono. "Ogni endpoint deve avere un test di permesso" è una bella frase nella constitution. Ma se nessuno la controlla, alla terza feature non è più vera.

C'è anche un problema di ambiente. "Sul mio computer funziona" è la frase più famosa dello sviluppo software. Il mio computer ha versioni diverse delle librerie, un database già pieno, variabili d'ambiente dimenticate. La CI parte ogni volta da zero.

## Come funziona

Pensa ai controlli di sicurezza in aeroporto. Non importa quanto sei sicuro di non avere niente di pericoloso in valigia: passi comunque dal metal detector. E non decidi tu se passare. È il sistema che decide. La CI è il metal detector del codice: ogni modifica passa dagli stessi controlli, sempre, senza eccezioni.

Una pipeline di CI è una sequenza di passi definita in un file del repository. A ogni evento, per esempio un push o una pull request, un server avvia una macchina pulita, scarica il codice, installa le dipendenze ed esegue i comandi. Se un comando restituisce un errore, la pipeline è rossa.

Il quality gate è l'ultimo pezzo: la piattaforma impedisce il merge se la pipeline è rossa. Su GitHub si chiama **branch protection**. Si configura sul branch principale indicando quali controlli sono obbligatori.

**pre-commit** è lo stesso concetto spostato sul computer dello sviluppatore. Prima di ogni commit esegue i controlli veloci. Così gli errori banali li vedi subito, non dieci minuti dopo il push.

## Come lo abbiamo applicato in MusicStudio

Il workflow è in `.github/workflows/ci.yml`. Un solo job, su Ubuntu, con due container di servizio: PostgreSQL 16 e Redis 7. I passi:

1. `uv sync --frozen`: installa le dipendenze esattamente come nel lockfile. Se il lockfile non corrisponde a `pyproject.toml`, fallisce.
2. `ruff check`: errori di lint, compresi controlli di sicurezza (regole `S` di bandit) e pratiche Django (regole `DJ`).
3. `ruff format --check`: la formattazione è quella standard.
4. `mypy`: i tipi sono coerenti, con i plugin per Django e DRF.
5. `makemigrations --check`: nessuno ha cambiato un modello dimenticando la migrazione.
6. `pytest`: tutti i test, con la copertura minima del 90%.
7. `spectacular --fail-on-warn`: lo schema OpenAPI si genera senza avvisi.

```yaml
- name: Migrations in sync
  run: uv run python manage.py makemigrations --check --dry-run --settings=config.settings.test

- name: Tests + coverage (fails under 90%)
  run: uv run pytest --cov-report=xml
```

In locale, `.pre-commit-config.yaml` esegue i controlli veloci: spazi finali, fine dei file, YAML e TOML validi, chiavi private nel codice, ruff, mypy e migrazioni. I test completi restano in CI, perché in locale richiederebbero troppo tempo a ogni commit.

**Due problemi pratici che ho risolto.**

Primo: la prima esecuzione di pre-commit ha modificato un file del frontend (`frontend/public/favicon.svg`, aggiungendo un "a capo" finale). Il frontend è fuori scope e non va toccato. Ho annullato la modifica ed escluso `frontend/`, `design/` e `.specify/` dagli hook.

Secondo: `pre-commit install` si rifiutava di funzionare. Su questo computer c'è un `core.hooksPath` globale, usato per sincronizzare il vault Obsidian dopo ogni commit. La soluzione è nella cartella `.githooks/` del repository: un hook `pre-commit` che lancia pre-commit e un hook `post-commit` che richiama quello globale. Si attivano una volta con `git config core.hooksPath .githooks`. Così funzionano entrambi.

**Cosa manca e va fatto da te.** Il "blocca il merge" richiede la branch protection su GitHub, con il check `ci / backend` obbligatorio. Non si attiva da codice. Inoltre il repository oggi non ha un branch `main`. Il piano consigliato è creare `main` da questo branch, dopo la tua revisione, e proteggerlo.

## Alternative considerate

**Un job per ogni strumento**, in parallelo. Il feedback arriva prima, ma ogni job ripete installazione e setup. Per un progetto piccolo costa più minuti di quanti ne risparmia.

**SQLite in CI** per velocità. Non testerebbe le funzionalità di PostgreSQL che usiamo.

**tox o nox** per orchestrare. Utili con più versioni di Python. Noi ne abbiamo una sola.

**GitLab CI o altri servizi.** Il codice è su GitHub, quindi GitHub Actions è la scelta naturale.

## Errori comuni e trade-off

- **CI senza branch protection.** La pipeline diventa rossa, ma si può fare merge lo stesso. Un semaforo senza conseguenze.
- **Dipendenze non bloccate.** Senza `--frozen` la CI potrebbe installare versioni diverse da quelle in locale.
- **CI troppo lenta.** Se ci mette mezz'ora, gli sviluppatori la aggirano. Oggi la nostra dura pochi minuti.
- **Test che falliscono a caso** (flaky). Distruggono la fiducia: dopo un po' ognuno rilancia senza guardare. Vanno corretti subito.
- **Trade-off di pre-commit:** mypy su tutto il progetto a ogni commit costa qualche secondo. Lo accetto, perché trova errori prima del push.

## Come lo spiegheresti a un colloquio

Ho una pipeline GitHub Actions che a ogni push esegue lint, formattazione, mypy, il controllo delle migrazioni, i test con copertura minima del 90% e la generazione dello schema OpenAPI. I test girano contro PostgreSQL e Redis veri come container di servizio, per essere uguali alla produzione. Le dipendenze sono installate dal lockfile con `--frozen`, quindi la build è riproducibile. In locale gli stessi controlli veloci girano con pre-commit. Il merge si blocca con la branch protection di GitHub, che rende il check obbligatorio.

## Domande di autoverifica

1. **Che differenza c'è tra CI e quality gate?**
   La CI esegue i controlli. Il quality gate è la regola che impedisce il merge se i controlli falliscono, e su GitHub si implementa con la branch protection.

2. **Perché `makemigrations --check` è in CI?**
   Per scoprire subito un modello cambiato senza la migrazione. Altrimenti il problema si vede solo durante il deploy.

3. **A cosa serve `uv sync --frozen`?**
   A installare esattamente le versioni del lockfile, e a fallire se il lockfile non è aggiornato. Così la build è riproducibile.

4. **Perché pre-commit non esegue i test completi?**
   Perché sarebbero troppo lenti a ogni commit. In locale girano i controlli veloci, la CI fa il resto.

5. **Perché `pre-commit install` non funzionava, e come l'hai risolto?**
   C'era un `core.hooksPath` globale. Ho creato hook versionati in `.githooks/` che eseguono pre-commit e richiamano l'hook globale, attivati con un `core.hooksPath` locale al repository.
