# Isolamento dei tenant e BOLA

## TL;DR

In un sistema multi-tenant ogni cliente deve vedere e modificare solo i propri dati. La vulnerabilità più comune delle API, chiamata BOLA (Broken Object Level Authorization), è proprio la mancanza di questo controllo su un singolo oggetto. MusicStudio filtrava bene le letture, ma non le scritture: un insegnante poteva creare lezioni e pagamenti sugli allievi di un altro. Ora anche i campi di relazione dei serializer sono filtrati per utente.

## Il problema reale

Un'API REST espone oggetti tramite il loro identificativo: `/api/v1/students/42/`. Un utente malintenzionato non deve indovinare niente di complicato. Gli basta cambiare il numero. Se il server non controlla che l'oggetto 43 appartenga davvero a quell'utente, i dati di un altro cliente sono esposti.

OWASP, l'organizzazione che pubblica le liste dei rischi di sicurezza più diffusi, mette BOLA al primo posto della sua classifica per le API. Non per caso: è facile da introdurre e i test "normali" non lo vedono, perché nei test di solito ogni utente usa i propri dati.

In MusicStudio la posta in gioco è alta. Ci sono dati di bambini e registrazioni di pagamenti. Una fuga tra famiglie, o tra insegnanti concorrenti, non è un bug qualsiasi: è la fine della fiducia nel prodotto.

## Come funziona

Pensa a un condominio con le cassette della posta. Il portiere ti dà la chiave della tua cassetta. Il controllo di sicurezza non è "sei un condomino?". È "questa è la **tua** cassetta?". Autenticazione e autorizzazione a livello di ruolo rispondono alla prima domanda. L'autorizzazione a livello di oggetto risponde alla seconda.

Ci sono due momenti in cui il controllo serve.

**In lettura.** Quando chiedi una lista o un oggetto, il server deve cercare solo tra gli oggetti visibili a te. Il modo più robusto è filtrare il queryset alla fonte, nel database. Un oggetto di un altro tenant non viene "vietato": per te non esiste. Per questo la risposta è 404 e non 403. Un 403 direbbe "esiste, ma non puoi", e rivelerebbe un'informazione.

**In scrittura.** Quando crei o modifichi un oggetto, i dati che invii possono contenere riferimenti ad altri oggetti: "crea una lezione per l'allievo 43". Anche quel riferimento va controllato. Ed è il punto che spesso si dimentica.

In Django REST Framework un campo di relazione, come `PrimaryKeyRelatedField`, valida l'id contro il proprio `queryset`. Per un `ModelSerializer` quel queryset è, di default, `Model.objects.all()`: qualsiasi id esistente nel database viene accettato.

## Come lo abbiamo applicato in MusicStudio

**Le letture erano già protette.** Una funzione di scoping, oggi `scope` in `backend/apps/common/scoping.py` (nella fase 1 si chiamava `role_scoped_queryset`), filtra un queryset in base al ruolo: l'insegnante vede i propri allievi, il titolare tutti quelli del suo studio, il genitore solo i figli collegati. Ogni ViewSet la usava.

**Le scritture no.** Durante l'audit ho fatto un test semplice. L'insegnante A manda un POST a `/api/v1/lessons/` con l'id di un allievo dell'insegnante B. Risposta: 201 Created. Stessa cosa per `/api/v1/payments/`. La lezione finiva davvero nell'agenda di B.

La correzione è un mixin in `backend/apps/common/serializers.py`:

```python
class ScopedRelatedFieldsMixin(serializers.Serializer[Any]):
    scoped_fields = {"student": students_visible_to, "package": packages_visible_to}

    def get_fields(self):
        fields = super().get_fields()
        user = getattr(self.context.get("request"), "user", None)
        for name, scope in self.scoped_fields.items():
            field = fields.get(name)
            if isinstance(field, serializers.PrimaryKeyRelatedField) and not field.read_only:
                field.queryset = scope(user)
        return fields
```

A ogni richiesta il queryset del campo `student` diventa "gli allievi visibili a questo utente". Un id esterno diventa un normale errore 400 "Invalid pk", identico a quello di un id inesistente. Quindi non rivela nemmeno se l'oggetto esiste. Il mixin è applicato ai serializer di lezioni, pagamenti e pacchetti.

Lo scoping da solo però non basta per una regola più fine. Un insegnante poteva collegare la lezione dell'allievo A al pacchetto dell'allievo B, entrambi suoi. Lo scoping lo permetteva, ma completando la lezione si scalava il pacchetto della famiglia sbagliata. Questa è una regola di dominio, e sta nel service `backend/apps/lessons/services.py`.

Durante il lavoro è emersa anche un'altra fuga. La view degli insegnanti dello studio faceva `Teacher.objects.filter(studio=teacher.studio)`. Se il titolare non aveva uno studio, il filtro diventava `studio IS NULL` e restituiva tutti gli insegnanti solisti di tutti i tenant, con la loro email. Ora `teachers_for_owner` in `backend/apps/studios/selectors.py` restituisce un queryset vuoto.

**I test.** Ogni endpoint di scrittura ha un test "cross tenant": `backend/apps/lessons/tests/test_cross_tenant_writes.py`, e gli equivalenti per pagamenti e pacchetti. Coprono creazione, spostamento su un allievo esterno e pacchetto esterno. Controllano lo status 400 **e** che nel database non sia stato scritto niente.

## Alternative considerate

**Controlli in ogni `perform_create`.** Funziona, ma va ripetuto in ogni view e nei metodi di update, dove è facile dimenticarlo.

**Permessi a livello di oggetto di DRF** (`has_object_permission`). Si applicano all'oggetto della URL, non agli oggetti referenziati nel corpo della richiesta. Non risolvono questo caso.

**Row Level Security di PostgreSQL.** Il database stesso filtra le righe in base all'utente della sessione. È la difesa più forte, ma con Django richiede di passare l'identità del tenant alla connessione a ogni richiesta. È un'opzione da valutare nella fase 2, con la multi-tenancy esplicita.

## Errori comuni e trade-off

- **Proteggere solo le letture.** È esattamente l'errore che avevamo.
- **Rispondere 403 a un oggetto di un altro tenant.** Rivela che esiste. Meglio 404 in lettura e 400 generico in scrittura.
- **Fidarsi del frontend.** Se l'interfaccia mostra solo i propri allievi, nessuno impedisce a un client di mandare un altro id.
- **`filter(campo=None)` per sbaglio.** Se una variabile è `None`, Django filtra per `IS NULL`. In un sistema multi-tenant può diventare "tutti i record senza tenant".
- **Trade-off, e come è evoluto:** nella fase 1 lo scoping aveva tre rami ripetuti per ogni modello. Nella fase 2 lo studio è diventato un tenant esplicito, obbligatorio per insegnanti e allievi, e lo scoping riceve un contesto calcolato una volta per richiesta. Vedi `docs/learning/concetti/multi-tenancy.md`.

## Come lo spiegheresti a un colloquio

Il rischio principale di un'API multi-tenant è BOLA: un utente che accede o scrive oggetti di un altro tenant cambiando un id. In MusicStudio le letture erano filtrate nel queryset, ma i campi di relazione dei serializer validavano gli id contro tutta la tabella, e un insegnante poteva creare lezioni sugli allievi di un altro. L'ho dimostrato con un test, poi ho scritto un mixin che restringe a ogni richiesta il queryset dei campi `student` e `package` agli oggetti visibili all'utente. Un id esterno diventa un 400 indistinguibile da un id inesistente. Ogni endpoint di scrittura ora ha un test che verifica il rifiuto e che nel database non sia stato scritto niente.

## Domande di autoverifica

1. **Cos'è BOLA?**
   Broken Object Level Authorization: il server non verifica che l'oggetto richiesto o referenziato appartenga all'utente. È il primo rischio della OWASP API Security Top 10.

2. **Perché un oggetto di un altro tenant restituisce 404 e non 403?**
   Il 403 conferma che l'oggetto esiste. Con il 404 l'oggetto, per quell'utente, semplicemente non c'è.

3. **Perché il `ModelSerializer` permetteva la scrittura cross-tenant?**
   Il campo di relazione valida l'id contro `Model.objects.all()`, quindi accetta qualsiasi oggetto esistente nel database.

4. **Perché lo scoping non basta per il pacchetto della lezione?**
   Lo scoping dice "è un pacchetto di un tuo allievo". La regola di dominio è più stretta: deve essere il pacchetto dello stesso allievo della lezione. Quella regola sta nel service.

5. **Cosa deve controllare un buon test cross-tenant in scrittura?**
   Lo status di errore e che nel database non sia stato creato o modificato nulla.
