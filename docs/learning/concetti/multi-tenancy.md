# Multi-tenancy: lo studio come tenant

## TL;DR

Multi-tenancy significa che un solo sistema serve molti clienti separati, chiamati tenant, e ognuno vede solo i suoi dati. In MusicStudio il tenant è lo studio. Nella fase 2 lo studio è diventato obbligatorio per ogni insegnante e ogni allievo: un insegnante solista ha uno studio personale. A ogni richiesta il sistema calcola una volta sola "chi sei e in quale studio", e usa quel contesto per filtrare tutti i dati.

## Il problema reale

Un SaaS ha molti clienti nello stesso database. Lo studio Rossi e lo studio Bianchi hanno le loro tabelle di allievi mescolate nella stessa tabella. Ogni query deve dire "solo quelli dello studio Rossi". Se una query se ne dimentica, i dati di un cliente finiscono a un altro.

Nella fase 1 il confine tra clienti non era esplicito. Un insegnante solista non aveva uno studio. La visibilità era decisa da tre rami di codice: "se sei titolare filtra così, se sei insegnante filtra così, se sei genitore filtra così". E in quel codice l'audit ha trovato due fughe. La prima: i campi di relazione accettavano allievi di altri insegnanti. La seconda: un titolare senza studio vedeva tutti gli insegnanti solisti, perché il filtro diventava "studio vuoto".

Il problema di fondo era che il tenant non esisteva come concetto nel database. Era una convenzione sparsa nel codice.

## Come funziona

Pensa a un condominio. Gli appartamenti sono nello stesso edificio, condividono le scale e l'ascensore, ma ognuno ha la sua porta e la sua chiave. Il sistema multi-tenant è l'edificio. Il tenant è l'appartamento. La regola fondamentale è che ogni oggetto in casa appartiene a un appartamento preciso, e che la chiave funziona solo per quello.

Ci sono tre modi classici di fare multi-tenancy.

**Database separato per tenant.** Il massimo isolamento, ma tanti database da gestire, migrare e pagare.

**Schema separato per tenant**, nello stesso database. In Django lo fa la libreria django-tenants. Buon isolamento, ma ogni migrazione va applicata a ogni schema.

**Tabelle condivise con una colonna tenant.** Tutti nello stesso posto, e ogni riga dice a quale tenant appartiene. È il modello più semplice da gestire e quello più comune nei SaaS piccoli e medi. Il rischio è dimenticare il filtro, quindi il filtro deve stare in un punto solo.

Noi usiamo il terzo modello. Due idee lo rendono sicuro.

La prima: **la colonna tenant è obbligatoria**. Se il database non permette un insegnante senza studio, il filtro "studio vuoto" non può più esistere.

La seconda: **il contesto del tenant si calcola una volta**, all'inizio della richiesta, e tutto il resto lo usa. Nessun pezzo di codice deve ricostruire da solo "chi è l'utente".

## Come lo abbiamo applicato in MusicStudio

**Le migrazioni.** In `backend/apps/studios/migrations/0003_personal_studios.py` ogni insegnante senza studio riceve uno studio personale, con il suo nome, e ne diventa il titolare. La migrazione `0004` rende lo studio obbligatorio, con `on_delete=PROTECT`, così cancellare uno studio con insegnanti dentro è impossibile. Poi `backend/apps/students/migrations/` aggiunge lo studio a ogni allievo, copiandolo dal suo insegnante, e lo rende obbligatorio.

Le migrazioni sono divise in file separati per un motivo pratico. PostgreSQL rifiuta di modificare una tabella nella stessa transazione in cui ci sono aggiornamenti con controlli di chiave esterna ancora in sospeso.

Un test, `test_migration_gives_every_teacher_and_student_a_studio` in `backend/apps/common/tests/test_tenancy.py`, porta il database indietro al formato della fase 1, crea un insegnante solista senza studio, applica le migrazioni vere e controlla il risultato.

**Il contesto.** In `backend/apps/common/tenancy.py`:

```python
@dataclass(frozen=True)
class TenantContext:
    user_id: int | None
    role: str | None
    studio_id: int | None = None
    teacher_id: int | None = None
    parent_id: int | None = None
```

`get_tenant(request)` lo costruisce con una sola query e lo salva sulla richiesta Django. Le chiamate successive nella stessa richiesta lo riusano: un test controlla che due chiamate facciano una sola query.

Perché non un middleware? Perché l'autenticazione JWT avviene dentro DRF, dopo i middleware. Quando il middleware gira, l'utente non è ancora noto.

**Lo scoping.** In `backend/apps/common/scoping.py` ogni modello dichiara una volta come raggiungere studio, insegnante e genitore:

```python
LESSON_PATHS = TenantPaths(
    studio="student__studio", teacher="teacher", parent="student__parent_accounts"
)
```

La funzione `scope(queryset, ctx, paths)` applica la regola: il titolare vede il suo studio, l'insegnante i suoi oggetti, il genitore i suoi figli, gli altri niente.

**Dove sta lo studio.** Solo su insegnanti e allievi. Lezioni, pacchetti e pagamenti lo raggiungono tramite l'allievo. L'allievo è la "radice" di tutti i dati di una famiglia.

**Il prima e dopo.** Prima: tre rami ripetuti in ogni selector, e un titolare senza studio che vedeva insegnanti di altri. Dopo: un contesto calcolato una volta, una funzione di scoping, e uno studio che non può mancare. Tutti i test di isolamento della fase 1 passano ancora, e i budget di query sono rimasti identici.

## Alternative considerate

**Lo studio su ogni tabella.** Filtri più diretti, senza join. Ma quattro tabelle in cui tenere coerente lo studio. Lo rivaluteremo solo se il profiling lo chiederà.

**django-tenants**, uno schema per tenant. Isolamento migliore, ma ogni migrazione moltiplicata per il numero di studi. Per studi da uno a dieci insegnanti è eccessivo.

**Row Level Security di PostgreSQL.** Il database stesso filtra le righe in base al tenant della sessione. È la garanzia più forte, perché protegge anche da una query scritta male. Ma richiede di impostare il tenant sulla connessione a ogni richiesta. La valuteremo nella fase 4.

**Contesto in una variabile globale** (thread-local). Comodo, ma implicito e pericoloso se non viene azzerato tra una richiesta e l'altra.

## Errori comuni e trade-off

- **Colonna tenant opzionale.** Un `NULL` diventa un tenant fantasma che filtra "tutto ciò che non ha tenant".
- **Filtro ripetuto a mano in ogni query.** Prima o poi qualcuno lo dimentica. Deve stare in un punto solo.
- **Ricalcolare il contesto più volte.** Query sprecate e possibili incoerenze.
- **Trade-off dichiarato:** la regola "lo studio dell'allievo è quello del suo insegnante" è garantita dai service, non dal database. Una scrittura diretta nell'admin potrebbe violarla.
- **I genitori non hanno uno studio.** Un genitore può avere figli in studi diversi, quindi per lui il "tenant" sono i collegamenti con i figli.

## Come lo spiegheresti a un colloquio

È un SaaS multi-tenant con tabelle condivise, e il tenant è lo studio. Nella fase 2 ho reso lo studio obbligatorio per insegnanti e allievi, con una migrazione che dà a ogni solista uno studio personale, e un test che applica la migrazione a dati del formato precedente. A ogni richiesta calcolo una volta un contesto immutabile con ruolo, studio e profilo, e lo metto in cache sulla richiesta, perché con JWT un middleware non conosce ancora l'utente. Tutto lo scoping passa da una funzione che riceve il contesto e i percorsi del modello verso il tenant. Ho scartato uno schema per tenant perché per questa scala moltiplicherebbe le migrazioni senza un vero beneficio.

## Domande di autoverifica

1. **Quali sono i tre modelli classici di multi-tenancy?**
   Database per tenant, schema per tenant, e tabelle condivise con una colonna tenant. Noi usiamo il terzo.

2. **Perché rendere lo studio obbligatorio migliora la sicurezza?**
   Perché elimina il caso "studio vuoto", che nella fase 1 trasformava un filtro in "tutti gli insegnanti senza studio".

3. **Perché il contesto non si calcola in un middleware?**
   Perché l'autenticazione JWT avviene dentro DRF, dopo i middleware: lì l'utente non è ancora noto.

4. **Perché lezioni, pacchetti e pagamenti non hanno una colonna studio?**
   Perché raggiungono lo studio tramite l'allievo. Una colonna su ogni tabella darebbe filtri più diretti, ma quattro posti da tenere coerenti.

5. **Qual è il punto debole del nostro modello?**
   La coerenza tra lo studio dell'allievo e quello del suo insegnante è garantita dai service, non da un vincolo nel database.
