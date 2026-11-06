# Strategia di test

## TL;DR

I test di MusicStudio girano con pytest su un PostgreSQL vero e usano factory_boy per creare i dati. Si concentrano su tre cose: le regole di business, i confini tra tenant e il numero di query. Siamo passati da 26 a 92 test e la copertura del codice è al 96%, con una soglia minima del 90% che blocca la CI. La copertura non è l'obiettivo: è un allarme per il codice dimenticato.

## Il problema reale

Senza test, ogni modifica è una scommessa. In questa fase abbiamo spostato quasi tutta la logica da modelli e view ai service. Senza una rete di sicurezza non avremmo potuto dire "il comportamento è rimasto lo stesso".

Ma anche con i test ci sono trappole. Si possono avere molti test che non controllano le cose importanti. I 26 test iniziali di MusicStudio erano buoni, ma nessuno provava a scrivere un dato nel tenant di un altro. Per questo la falla delle scritture cross-tenant era passata inosservata.

E c'è il problema della fiducia nell'ambiente. Se i test girano su SQLite e la produzione su PostgreSQL, alcune cose (vincoli, indici parziali, lock di riga) non vengono testate davvero.

## Come funziona

Pensa ai controlli di un'auto prima di un viaggio. Non controlli ogni vite. Controlli freni, gomme, luci e olio: le cose che, se si rompono, causano un incidente. Una buona strategia di test fa lo stesso: concentra lo sforzo dove un errore costa di più.

Gli strumenti che usiamo:

**pytest** è il test runner. I test sono funzioni semplici con `assert`. Le fixture forniscono risorse condivise, come un database pulito.

**pytest-django** collega pytest a Django. Il marcatore `django_db` dà a ogni test una transazione che viene annullata alla fine, così i test non si sporcano a vicenda.

**factory_boy** crea oggetti di test con valori sensati. Invece di scrivere a mano utente, insegnante, studio e allievo, scrivi `StudentFactory()`. Se ti serve un caso particolare, sovrascrivi solo il campo che conta: `PackageFactory(lessons_remaining=0)`.

**pytest-cov** misura quali righe e quali rami del codice sono stati eseguiti dai test.

**`django_assert_num_queries`** e `CaptureQueriesContext` contano le query eseguite da un blocco di codice.

## Come lo abbiamo applicato in MusicStudio

La configurazione è in `backend/pyproject.toml`: impostazioni di test `config.settings.test`, copertura su `apps` e `config` con i rami, soglia `--cov-fail-under=90`.

Le factory sono in `backend/apps/common/factories.py`. Gli helper sono in `backend/apps/common/tests/helpers.py`: `client_for(user)` crea un client autenticato e `make_studio_owner()` prepara un titolare con il suo studio.

Le categorie di test che abbiamo ora:

**Regole di business.** Per esempio `backend/apps/lessons/tests/test_completion.py` e `test_services.py`: completare una lezione scala il pacchetto una sola volta, non sotto zero, anche se due richieste arrivano con lo stesso oggetto in memoria.

**Confini tra tenant.** I file `test_cross_tenant_writes.py` in lezioni, pagamenti e pacchetti. Ogni test controlla lo status 400 e che nel database non ci sia nulla di nuovo:

```python
res = client_for(attacker.user).post(
    "/api/v1/lessons/", {"student": victim_student.id, "start_time": START}
)
assert res.status_code == 400
assert not Lesson.objects.filter(student=victim_student).exists()
```

**Budget di query.** `backend/apps/common/tests/test_num_queries.py` misura ogni endpoint principale con 1 e con 25 righe e confronta con un numero fisso.

**Infrastruttura.** I controlli di salute in `backend/config/tests/test_health.py`, che simulano un database o un Redis non raggiungibile sostituendo la funzione di controllo. Le impostazioni di produzione in `test_settings.py`, caricate in un processo separato.

**Regressioni dei difetti trovati.** Ogni bug dell'audit ha il suo test: settimana non valida, titolare senza studio, pacchetto creato senza contatore, promemoria reclamato da uno sweep concorrente.

**Il prima e dopo.** Prima: 26 test, nessuna misura di copertura. Dopo: 92 test, copertura al 96% (righe e rami). I 26 test originali sono passati dopo il refactoring, cambiando solo le chiamate dai metodi del modello ai service. Questa è la prova che il comportamento è rimasto lo stesso.

**Una scelta discutibile, detta chiaramente.** mypy controlla il codice di produzione in modo rigoroso, ma non i test. Il motivo: mypy non capisce che `StudentFactory()` restituisce uno `Student`, perché ignora il `__new__` di factory_boy. Tipizzare i test avrebbe voluto dire riscriverli tutti con `StudentFactory.create()`, per un beneficio piccolo. I test sono comunque verificati eseguendoli.

## Alternative considerate

**SQLite per velocità.** I test sarebbero più veloci, ma non testerebbero gli indici parziali, `select_for_update` e i vincoli di PostgreSQL. In CI usiamo un PostgreSQL 16 vero.

**Fixture JSON invece delle factory.** Dati fissi e uguali per tutti i test. Diventano presto illeggibili e fragili, e nascondono quale dato conta per il test.

**Test end-to-end con un browser.** Il frontend è fuori scope. Per un'API, i test con il client DRF coprono il contratto HTTP.

**Mock del database.** Test velocissimi ma che non provano niente sulle query reali, che sono proprio uno dei nostri rischi principali.

## Errori comuni e trade-off

- **Inseguire il 100% di copertura.** Porta a test inutili su codice banale. La soglia del 90% serve a non dimenticare pezzi interi, non a misurare la qualità.
- **Testare solo il caso felice.** I bug più gravi stanno nei casi negativi, come il tentativo di scrivere nel tenant di un altro.
- **Test che dipendono dall'ordine o dal tempo.** Le date relative a "adesso" possono fallire a mezzanotte o nei cambi d'ora. Dove conta, usiamo date fisse.
- **Asserire l'implementazione invece del comportamento.** Un test deve dire "il pacchetto scende a 7", non "è stato chiamato il metodo X".
- **Il conteggio delle query con utenti in cache.** `force_authenticate` riusava l'utente della factory. Ora l'helper ricarica l'utente dal database, come una richiesta vera.
- **Trade-off:** PostgreSQL vero rende i test più lenti (circa 13 secondi). È un prezzo accettabile per la fiducia che dà.

## Come lo spiegheresti a un colloquio

Uso pytest con factory_boy contro un PostgreSQL vero, sia in locale sia in CI, perché uso funzionalità specifiche di Postgres. Concentro i test su tre rischi: regole di business, isolamento tra tenant e numero di query. Ogni endpoint di scrittura ha un test che prova a scrivere nel tenant di un altro e verifica che nel database non arrivi niente. Gli endpoint principali hanno un budget di query fisso, misurato con 1 e con 25 righe. La copertura è al 96% con una soglia del 90% in CI, ma la uso come allarme, non come obiettivo.

## Domande di autoverifica

1. **Perché i test girano su PostgreSQL e non su SQLite?**
   Perché usiamo funzionalità di PostgreSQL, come indici parziali, `select_for_update` e vincoli, che SQLite non ha o gestisce diversamente.

2. **Cosa rende utile factory_boy?**
   Crea oggetti completi con valori sensati, e nel test scrivi solo il dato che conta per quel caso.

3. **Perché la soglia di copertura è al 90% e non al 100%?**
   Il 100% spinge a scrivere test inutili. Il 90% segnala il codice dimenticato senza diventare un obiettivo fine a sé stesso.

4. **Come hai dimostrato che il refactoring non ha cambiato il comportamento?**
   I 26 test originali sono passati dopo lo spostamento della logica nei service, cambiando solo il punto di chiamata.

5. **Perché mypy non controlla i test?**
   Perché non riesce a tipizzare le chiamate alle factory di factory_boy. Sarebbe solo rumore, e i test sono già verificati eseguendoli.
