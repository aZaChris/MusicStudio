# Service layer e modular monolith

## TL;DR

Un modular monolith è un'unica applicazione deployabile, divisa all'interno in moduli per dominio. In MusicStudio ogni dominio è un'app Django. Dentro ogni app, la logica di business vive in due file precisi: `services.py` per le scritture e `selectors.py` per le letture. View e serializer diventano sottili: ricevono la richiesta, chiamano il service, restituiscono la risposta.

## Il problema reale

Django ti lascia mettere la logica dove vuoi. Nel metodo `save()` del modello. In una property. Nel `create()` del serializer. Dentro la view. All'inizio sembra comodo. Poi il progetto cresce, e succedono tre cose.

Prima cosa: non trovi più le regole. In MusicStudio, per sapere cosa succede quando si crea una lezione, dovevi leggere il serializer (che sceglieva il pacchetto di default), il modello (che aveva `mark_completed`) e la view (che chiamava il metodo). Tre file per una sola regola.

Seconda cosa: le query si nascondono. La property `Student.active_package` faceva una query al database. Sembrava un semplice attributo. Usata in un ciclo, diventava una query per ogni allievo.

Terza cosa: non puoi testare la regola senza l'HTTP. Se la logica sta nella view, per provarla devi simulare una richiesta, autenticare un utente, leggere un JSON. Lento e fragile.

## Come funziona

Pensa a un ristorante. Il cameriere prende l'ordine e lo porta in cucina. Non cucina lui. La cucina prepara il piatto, sempre allo stesso modo, che l'ordine arrivi dal cameriere, dal telefono o dal servizio di consegna. Il cameriere è la view. La cucina è il service layer.

Il service layer è uno strato di funzioni che contiene i casi d'uso dell'applicazione. "Crea una lezione". "Completa una lezione". "Registra un pagamento". Ogni funzione riceve dati già validati, applica le regole, scrive nel database dentro una transazione e restituisce il risultato.

Accanto ai service ci sono i selector. Un selector è una funzione che legge. Restituisce un queryset già filtrato per l'utente, con le relazioni precaricate. Così la view non deve sapere come si evita una query N+1: chiama il selector e basta.

Il "modular monolith" è la scelta di architettura che sta intorno. Monolite, perché c'è un solo processo da deployare, un solo database, una sola pipeline. Modulare, perché il codice è diviso per dominio con confini chiari: `accounts`, `studios`, `students`, `packages`, `lessons`, `payments`, `notifications`. Un modulo usa un altro modulo tramite i suoi modelli, service e selector, mai tramite le sue view.

## Come lo abbiamo applicato in MusicStudio

Ogni app ha ora `services.py` e `selectors.py`. Per esempio:

- `backend/apps/lessons/services.py`: `create_lesson`, `update_lesson`, `complete_lesson`, `cancel_lesson`.
- `backend/apps/lessons/selectors.py`: `lessons_for`, `lessons_in_week`, `upcoming_lessons_for`, `dashboard_for`.
- `backend/apps/payments/services.py`: `ensure_package_matches_student`, `create_payment`, `update_payment`.
- `backend/apps/students/selectors.py`: `students_for`, con pacchetti e ultimo pagamento precaricati.

**Prima.** La dashboard era scritta dentro `DashboardView.get`: quattro queryset costruiti a mano, un import dentro la funzione per evitare un ciclo e un filtro Python su ogni allievo. La regola "il pacchetto del pagamento deve appartenere allo stesso allievo" era scritta due volte, nel modello e nel serializer.

**Dopo.** La view della dashboard è una riga:

```python
def get(self, request: Request) -> Response:
    return Response(DashboardSerializer(selectors.dashboard_for(request.user)).data)
```

E la creazione di una lezione passa dal service nella view:

```python
def perform_create(self, serializer: LessonSerializer) -> None:
    serializer.instance = services.create_lesson(**serializer.validated_data)
```

I service sollevano la `ValidationError` di Django, non quella di DRF. Così non dipendono dall'HTTP e possono essere chiamati anche da Celery, dall'admin o da un comando. Un piccolo exception handler in `backend/apps/common/exceptions.py` traduce quell'errore in una risposta 400.

Un esempio concreto del vantaggio: spostando `complete_lesson` nel service abbiamo visto un bug di concorrenza. Il vecchio metodo controllava lo stato sull'oggetto in memoria. Due richieste quasi simultanee potevano scalare il pacchetto due volte. Ora il service blocca la riga con `select_for_update` e scala il pacchetto con un solo `UPDATE` condizionato. Il test `test_complete_with_stale_instance_does_not_double_decrement` in `backend/apps/lessons/tests/test_services.py` lo dimostra senza toccare l'HTTP.

## Alternative considerate

**Fat models.** Tutta la logica nei metodi del modello. È lo stile classico di Django. Funziona per progetti piccoli, ma porta a `save()` sovrascritti e a property che fanno query. Ed era proprio lo stato di partenza.

**Repository pattern.** Una classe che avvolge l'ORM. In Java o in .NET ha senso. In Django duplica un ORM che è già un'astrazione, e nasconde strumenti utili come `select_related`.

**Microservizi.** Un servizio separato per ogni dominio. Per uno studio con dieci insegnanti significa rete, deploy multipli e consistenza distribuita senza nessun beneficio reale.

**DDD completo**, con aggregati, value object ed eventi di dominio. Ottimo per domini complessi. Qui sarebbe cerimonia.

Lo stile che abbiamo scelto è quello della guida di stile Django di HackSoft: funzioni semplici, argomenti keyword, nessuna classe dove non serve.

## Errori comuni e trade-off

- **Service che diventano view mascherate.** Un service non deve ricevere la `request`. Riceve dati puliti. L'eccezione accettabile è passare l'utente, per lo scoping.
- **Mettere tutto nei service, anche il CRUD banale.** Se un'operazione è solo "salva questi campi", un `ModelViewSet` va benissimo. Il service serve quando c'è una regola.
- **Dimenticare la transazione.** Un caso d'uso che scrive in più tabelle deve stare in `transaction.atomic`.
- **Il trade-off principale è la disciplina.** Niente impedisce tecnicamente di rimettere logica in una view. Per questo la regola è nella constitution (Principio V) e va controllata in review.
- **Un costo onesto:** più file e un livello di indirezione in più. Per un CRUD puro sembra eccessivo. Il vantaggio si vede quando le regole crescono.

## Come lo spiegheresti a un colloquio

Il backend è un monolite modulare: un solo deploy, ma un'app Django per ogni dominio. Dentro ogni app separo le scritture in `services.py` e le letture complesse in `selectors.py`. View e serializer sono sottili: validano l'input e chiamano il service. Così le regole di business stanno in un punto solo, si testano senza HTTP e si riusano da Celery e dall'admin. Ho scelto un monolite perché per questa scala i microservizi aggiungerebbero solo costi operativi.

## Domande di autoverifica

1. **Che differenza c'è tra un service e un selector?**
   Il service scrive: applica regole, usa transazioni, modifica dati. Il selector legge: restituisce un queryset filtrato e ottimizzato, senza effetti collaterali.

2. **Perché i service sollevano la `ValidationError` di Django e non quella di DRF?**
   Per non dipendere dall'HTTP. Gli stessi service sono usati da Celery, admin e comandi. Un exception handler converte l'errore in 400 solo nel contesto API.

3. **Perché la property `active_package` era un problema?**
   Sembrava un attributo, ma faceva una query. In una lista di allievi diventava una query per allievo: un N+1 nascosto.

4. **Quale bug è emerso spostando `complete_lesson` nel service?**
   La doppia scalatura del pacchetto in caso di richieste concorrenti: il controllo dello stato avveniva sull'oggetto in memoria. Ora la riga è bloccata con `select_for_update`.

5. **Quando non serve un service?**
   Quando l'operazione è un CRUD senza regole. In quel caso un `ModelViewSet` standard è sufficiente e più leggibile.
