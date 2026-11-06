# Permessi DRF: per azione e per oggetto

## TL;DR

Django REST Framework controlla i permessi a due livelli. Il primo è la vista: "questo ruolo può chiamare questa azione?". Il secondo è l'oggetto: "questo utente può modificare questo oggetto preciso?". In MusicStudio la visibilità arriva prima, dal queryset filtrato per tenant. I permessi decidono cosa si può fare su ciò che si vede. Nella fase 2 abbiamo aggiunto il permesso per oggetto, lo spostamento di un allievo tra insegnanti e il limite di dieci insegnanti per studio.

## Il problema reale

Fino alla fase 1 la regola era semplice: gli insegnanti e i titolari scrivono, tutti gli autenticati leggono, e il queryset filtrato decide cosa si vede. Funzionava, ma "visibile" e "modificabile" erano la stessa cosa. Non c'era modo di dire "il titolare vede tutto lo studio, ma solo lui può spostare un allievo da un insegnante all'altro".

Inoltre due regole di prodotto non avevano nessuna protezione. Spostare un allievo a un altro insegnante non era possibile. E il limite di dieci insegnanti per studio, scritto nelle impostazioni, non era controllato da nessuna parte.

## Come funziona

Pensa a un museo. Il biglietto ti fa entrare nelle sale aperte al pubblico: è il primo livello, "puoi stare qui?". Ma dentro una sala, puoi guardare un quadro e non toccarlo. Il restauratore invece può toccare solo i quadri che gli sono stati assegnati. È il secondo livello, sul singolo oggetto.

In DRF ogni classe di permesso può implementare due metodi.

**`has_permission(request, view)`** viene chiamato per ogni richiesta, prima di tutto. Non conosce l'oggetto. Serve per le regole di ruolo: "solo i titolari possono chiamare questa azione".

**`has_object_permission(request, view, obj)`** viene chiamato quando la vista recupera un oggetto preciso, con `get_object()`. Serve per le regole che dipendono dall'oggetto: "puoi modificarlo solo se è dei tuoi allievi".

Un dettaglio importante: il permesso per oggetto **non** viene chiamato nelle liste e nella creazione. Nella lista ci pensa il queryset filtrato. Nella creazione ci pensa la validazione dei campi di relazione.

C'è anche un ordine da capire. In MusicStudio il queryset è già filtrato per tenant. Quindi se chiedi un oggetto di un altro studio, ricevi 404 prima che il permesso venga controllato. Il permesso per oggetto lavora solo su ciò che vedi. Se lo vedi ma non puoi modificarlo, ricevi 403.

## Come lo abbiamo applicato in MusicStudio

I permessi sono in `backend/apps/common/permissions.py`.

`IsTeacherOrStudioOwner` è il livello vista: lettura per tutti gli autenticati, scrittura solo per insegnanti e titolari.

`IsStudioOwner` permette un'azione solo ai titolari.

`CanWriteTenantObject` è il nuovo livello oggetto:

```python
def has_object_permission(self, request, view, obj):
    if request.method in SAFE_METHODS:
        return True
    ctx = get_tenant(request)
    studio_id, teacher_id = obj.tenant_keys()
    if ctx.is_owner:
        return studio_id == ctx.studio_id
    if ctx.is_teacher:
        return teacher_id == ctx.teacher_id
    return False
```

Ogni modello espone `tenant_keys()`, cioè la coppia (studio, insegnante responsabile). Così il permesso non deve conoscere la struttura di ogni modello. Le viste di allievi, lezioni, pacchetti e pagamenti usano `[IsTeacherOrStudioOwner, CanWriteTenantObject]`.

**Lo spostamento di un allievo.** In `backend/apps/students/views.py` c'è l'azione `POST /api/v1/students/{id}/reassign/` con `permission_classes=[IsStudioOwner]`. Il serializer accetta solo insegnanti dello studio del titolare: un insegnante di un altro studio dà 400. Il service `reassign_student` in `backend/apps/students/services.py` ricontrolla la regola, così vale anche se qualcuno lo chiama da un altro punto del codice. Le lezioni già create mantengono il loro insegnante. È una scelta voluta: la storia resta vera, e l'agenda del nuovo insegnante non si riempie di lezioni che non ha programmato.

I test in `backend/apps/students/tests/test_reassign.py` coprono tutti i casi: titolare nello stesso studio (200), verso un altro studio (400), allievo di un altro studio (404), insegnante e genitore (403).

**Il limite di dieci insegnanti.** In `backend/apps/studios/services.py`, `add_teacher_to_studio` blocca la riga dello studio con `select_for_update` e poi conta. Senza il blocco, due aggiunte contemporanee potrebbero leggere "nove" entrambe e arrivare a undici. `Teacher.clean()` usa la stessa regola, così anche l'admin di Django la rispetta.

**Il prima e dopo.** Prima: scrivere era permesso a chiunque avesse un ruolo da insegnante e vedesse l'oggetto. Lo spostamento di un allievo non esisteva. Il limite di insegnanti non era controllato. Dopo: una regola di scrittura esplicita per oggetto, un'azione riservata al titolare con test per ogni ruolo, e un limite protetto anche dalla concorrenza.

## Alternative considerate

**django-guardian o django-rules.** Permessi salvati per singolo oggetto nel database, tipo "l'utente X può modificare l'allievo 42". Sono utili quando i permessi si concedono uno per uno. Le nostre regole invece derivano dal tenant e dal ruolo, quindi sarebbero una tabella in più senza bisogno.

**Solo lo scoping del queryset.** Non può esprimere "lo vedi ma non lo modifichi".

**Controlli dentro le viste con degli `if`.** Funzionano, ma si ripetono e si dimenticano. Le classi di permesso si dichiarano una volta e DRF le applica sempre.

**Spostare anche le lezioni future.** Più comodo per l'utente, ma potrebbe creare sovrapposizioni nell'agenda del nuovo insegnante. Rimandato.

## Errori comuni e trade-off

- **Pensare che `has_object_permission` protegga le liste.** Non viene chiamato. Le liste si proteggono con il queryset.
- **Dimenticare `get_object()` nelle azioni personalizzate.** Se un'azione recupera l'oggetto a mano, il permesso per oggetto non viene eseguito.
- **Restituire 403 per oggetti di altri tenant.** Rivela che esistono. Noi rispondiamo 404, grazie al queryset filtrato.
- **Contare senza blocco.** I limiti numerici, come il massimo di insegnanti, hanno una race condition se non si blocca qualcosa prima di contare.
- **Trade-off:** oggi il permesso per oggetto è in parte ridondante con lo scoping. È difesa in profondità: se un giorno un queryset diventasse troppo largo per errore, la scrittura resterebbe bloccata.

## Come lo spiegheresti a un colloquio

Separo tre cose: la visibilità, che viene dal queryset filtrato per tenant e dà 404 fuori dal proprio studio; il permesso per azione, che controlla il ruolo; e il permesso per oggetto, che controlla se puoi modificare quell'oggetto specifico. Il permesso per oggetto è una classe DRF che legge dal modello la coppia studio e insegnante, e la confronta con il contesto dell'utente. Per lo spostamento di un allievo ho un'azione riservata al titolare, con il serializer che accetta solo insegnanti del suo studio e il service che ricontrolla la regola. Il limite di dieci insegnanti blocca la riga dello studio prima di contare, per evitare una race condition. Ho scartato librerie come django-guardian perché i miei permessi derivano dal tenant, non da concessioni individuali.

## Domande di autoverifica

1. **Che differenza c'è tra `has_permission` e `has_object_permission`?**
   Il primo è controllato per ogni richiesta e non conosce l'oggetto. Il secondo è controllato quando la vista recupera un oggetto con `get_object()`.

2. **Il permesso per oggetto protegge anche la lista degli allievi?**
   No. Nelle liste non viene chiamato. Le liste sono protette dal queryset filtrato.

3. **Perché un oggetto di un altro studio dà 404 e non 403?**
   Perché il queryset filtrato lo esclude prima del controllo dei permessi, e il 404 non rivela che esiste.

4. **Perché le lezioni non seguono l'allievo quando viene spostato?**
   Per non creare sovrapposizioni nell'agenda del nuovo insegnante e per tenere vera la storia di chi ha tenuto la lezione.

5. **Perché `add_teacher_to_studio` blocca la riga dello studio?**
   Per evitare che due aggiunte contemporanee leggano lo stesso conteggio e superino il limite.
