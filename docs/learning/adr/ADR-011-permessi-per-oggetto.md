# ADR-011: Permessi per azione e per oggetto

- Stato: accettato
- Data: 2026-11-06

## Contesto

Fino alla fase 1 la regola era: gli insegnanti scrivono, tutti leggono, e il queryset decide cosa si vede. Ma "visibile" e "modificabile" erano la stessa cosa. Inoltre mancavano due regole di prodotto: spostare un allievo a un altro insegnante, e il limite di 10 insegnanti per studio.

## Decisione

- Due livelli di permesso DRF:
  - `has_permission` (livello vista): questo ruolo può chiamare questa azione? Esempio: `IsTeacherOrStudioOwner`, `IsStudioOwner`.
  - `has_object_permission` (livello oggetto): questo utente può modificare *questo* oggetto? `CanWriteTenantObject`: il titolare modifica tutto nel suo studio, l'insegnante gli oggetti dei suoi allievi, il genitore niente.
- Ogni modello espone `tenant_keys()`, cioè (studio, insegnante responsabile), usato dal permesso.
- Nuova azione `POST /students/{id}/reassign/`, solo per il titolare, verso un insegnante dello stesso studio. Le lezioni già create **mantengono il loro insegnante**.
- Il limite di 10 insegnanti è nel service `add_teacher_to_studio`, che blocca la riga dello studio con `select_for_update` prima di contare. `Teacher.clean()` usa la stessa regola per l'admin.

## Alternative scartate

- **django-guardian o django-rules**: permessi salvati per oggetto nel database. Inutili: le nostre regole derivano dal tenant, non da concessioni individuali.
- **Solo lo scoping del queryset**: non può esprimere "lo vedi ma non lo modifichi".
- **Spostare anche le lezioni future con l'allievo**: potrebbe creare sovrapposizioni nell'agenda del nuovo insegnante. Rimandato a una funzione dedicata, se servirà.
- **Limite insegnanti con un trigger nel database**: logica nascosta in SQL.

## Conseguenze

- Il permesso a livello oggetto è oggi in parte ridondante con lo scoping. È difesa in profondità: se un giorno un queryset fosse troppo largo, il permesso blocca comunque la scrittura.
- Dopo un riassegnamento, il vecchio insegnante vede ancora le lezioni che ha tenuto. È voluto: la storia resta vera.
