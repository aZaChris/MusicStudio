# L'ORM e il problema N+1

## TL;DR

Il problema N+1 succede quando carichi una lista di N oggetti con una query e poi, per ognuno, fai un'altra query per leggere un dato collegato. In MusicStudio l'elenco degli allievi faceva 22 query per 10 allievi. Con `select_related`, `prefetch_related` e le annotazioni con `Subquery` il numero è diventato fisso: 4 query, con 1 allievo o con 25. Un test lo blocca per sempre.

## Il problema reale

L'ORM di Django è comodo perché nasconde l'SQL. Scrivi `student.teacher.user.email` e funziona. Ma ogni punto può essere una query al database. Se lo fai su un solo oggetto, non te ne accorgi. Se lo fai in un ciclo su cento oggetti, fai cento query.

Il caso classico è un serializer. Restituisci una lista di allievi e, per ognuno, il serializer chiede il pacchetto attivo e l'ultimo pagamento. Ogni campo è una query in più per ogni riga. Il codice è corto e sembra innocente. In sviluppo, con tre allievi, è veloce. In produzione, con trecento, la pagina rallenta e il database lavora cento volte più del necessario.

Il nome viene dal conto: 1 query per la lista, più N query, una per ogni elemento.

## Come funziona

Immagina di fare la spesa per una cena con dieci ospiti. Puoi andare al supermercato, comprare il pane, tornare a casa, rileggere la lista, tornare a comprare il vino, e così via per ogni ingrediente. Oppure leggi la lista intera e compri tutto in un solo viaggio. L'N+1 è il primo modo. Le ottimizzazioni dell'ORM sono il secondo.

Django offre tre strumenti principali.

**`select_related`** segue le foreign key "verso uno" con una JOIN. Se ogni lezione ha un allievo, `Lesson.objects.select_related("student")` porta lezioni e allievi in una sola query.

**`prefetch_related`** gestisce le relazioni "verso molti". Fa una seconda query con `WHERE id IN (...)` e collega i risultati in Python. Due query totali, sempre, invece di una per riga. Con l'oggetto `Prefetch` puoi filtrare e ordinare la seconda query e salvarne il risultato in un attributo a tua scelta con `to_attr`.

**Le annotazioni** calcolano un valore dentro la query principale. Con `Subquery` e `OuterRef` puoi chiedere "per ogni allievo, lo stato del suo ultimo pagamento" in SQL, senza tornare al database per ogni riga.

## Come lo abbiamo applicato in MusicStudio

Prima di correggere ho misurato, con un test temporaneo che contava le query.

**Prima:**

- `/api/v1/students/`: 4 query con 1 allievo, **22 con 10 allievi**. Due query in più per allievo: una per `active_package` (una property del modello) e una per `payment_status` (un `SerializerMethodField`).
- `/api/v1/dashboard/`: 5 query con 1 allievo, **14 con 10**. Il calcolo degli allievi con pacchetto in esaurimento chiamava `active_package` in un ciclo Python.
- `/api/v1/studio/teachers/`: una query per insegnante per leggere l'email dell'utente.
- Il task dei promemoria: una query per lezione per trovare i genitori.

**Dopo.** Il selector degli allievi in `backend/apps/students/selectors.py`:

```python
def students_for(user: Any) -> QuerySet[Student]:
    return (
        students_visible_to(user)
        .annotate(latest_payment_status=latest_payment_status_subquery())
        .prefetch_related(active_packages_prefetch())
    )
```

L'ultimo pagamento è una `Subquery` annotata. I pacchetti attivi arrivano con un `Prefetch` filtrato su `lessons_remaining > 0`, ordinato per data, in un attributo `active_packages`. La property `Student.active_package` in `backend/apps/students/models.py` usa la lista precaricata se c'è, e fa una query solo nei percorsi con un singolo oggetto, come la risposta a una creazione.

Per la dashboard, gli allievi con pacchetto in esaurimento sono ora una sola query annotata in `low_package_students_for` (`backend/apps/lessons/selectors.py`): una `Subquery` prende le lezioni rimaste del pacchetto attivo e il filtro avviene in SQL, non in Python.

Lo `StudioSerializer` usa un `Count` annotato invece di `teachers.count`. Gli insegnanti dello studio usano `select_related("user")`. Il task dei promemoria usa un `Prefetch` dei collegamenti genitore-allievo con i rispettivi utenti.

**Risultato:** allievi 4 query, lezioni 3, pacchetti 3, pagamenti 3, dashboard 6. Sempre uguali, con 1 riga o con 25.

**Il test che blocca le regressioni** è in `backend/apps/common/tests/test_num_queries.py`. Per ogni endpoint misura il numero di query con 1 e con 25 righe, e controlla che i due numeri siano uguali e pari al budget fissato. Se qualcuno aggiunge al serializer un campo che fa una query, il test fallisce e la CI blocca il merge.

Un dettaglio che ho imparato scrivendolo: `force_authenticate` nei test riutilizzava l'oggetto utente della factory, che aveva già in cache il profilo insegnante. Così il test contava una query in meno di una richiesta vera. Ora l'helper `client_for` in `backend/apps/common/tests/helpers.py` ricarica l'utente dal database, come farebbe l'autenticazione JWT.

## Alternative considerate

**Denormalizzare.** Salvare `latest_payment_status` direttamente sulla tabella degli allievi. Le letture diventano gratis, ma ogni scrittura su un pagamento deve aggiornare l'allievo, e i dati possono diventare incoerenti.

**Cache.** Mettere in cache la risposta della lista. Nasconde il problema invece di risolverlo, e introduce l'invalidazione. La cache è nel piano della fase 3, ma sopra query già efficienti.

**Strumenti di profiling come django-debug-toolbar o nplusone.** Utili per trovare il problema in sviluppo. Ma non bloccano le regressioni. Il test con il budget sì.

## Errori comuni e trade-off

- **`prefetch_related` dopo uno slice o un filtro sul related.** Se nel serializer scrivi `obj.packages.filter(...)`, il prefetch viene ignorato e torni all'N+1. Per questo il filtro sta nel `Prefetch`, con `to_attr`.
- **`select_related` su relazioni "verso molti".** Non funziona: serve `prefetch_related`.
- **Troppi `select_related`.** Una JOIN su molte tabelle può diventare più lenta di due query semplici. Misura.
- **Contare le query solo con pochi dati.** Con un solo record l'N+1 è invisibile. Il test deve confrontare 1 e N.
- **Trade-off dei budget fissi:** a volte cambiano per motivi legittimi, per esempio aggiungendo un campo. Allora si aggiorna il numero, consapevolmente, nella stessa PR.

## Come lo spiegheresti a un colloquio

L'N+1 è quando carichi una lista con una query e poi fai una query in più per ogni elemento, di solito dentro il serializer. In MusicStudio l'elenco degli allievi passava da 4 a 22 query con 10 allievi. Ho spostato le letture in selector che usano `prefetch_related` con `Prefetch` filtrato e annotazioni con `Subquery`. Ora ogni endpoint principale ha un numero di query costante. Un test confronta 1 e 25 righe e fallisce in CI se qualcuno reintroduce il problema.

## Domande di autoverifica

1. **Che differenza c'è tra `select_related` e `prefetch_related`?**
   `select_related` fa una JOIN e funziona per le relazioni verso uno (foreign key, one-to-one). `prefetch_related` fa una seconda query con `IN` e funziona anche per le relazioni verso molti.

2. **A cosa serve `to_attr` in un `Prefetch`?**
   Salva il risultato filtrato in un attributo dedicato, così il codice lo legge senza rifare la query e senza confonderlo con il manager completo.

3. **Perché il test misura con 1 e con 25 righe?**
   Perché l'N+1 si vede solo quando il numero di query cresce con i dati. Con un solo record il numero sembra normale.

4. **Perché `force_authenticate` falsava il conteggio?**
   Riutilizzava l'oggetto utente della factory, che aveva già in cache il profilo collegato. Una richiesta reale ricarica l'utente, quindi fa una query in più.

5. **Perché non abbiamo usato la cache per risolvere il problema?**
   La cache nasconde la query lenta invece di eliminarla e aggiunge il problema dell'invalidazione. Prima si rendono efficienti le query, poi, se serve, si aggiunge la cache.
