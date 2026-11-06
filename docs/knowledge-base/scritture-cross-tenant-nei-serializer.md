# KB: Scritture cross-tenant accettate dai serializer DRF

## Sintomo
Un insegnante poteva creare lezioni e pagamenti sugli allievi di un altro insegnante: `POST /api/v1/lessons/` con un `student` esterno rispondeva 201. I test di permesso esistenti erano tutti verdi.

## Causa radice
Lo scoping per tenant era applicato al queryset della view (letture e oggetto della URL), ma non ai campi di relazione del serializer. Un `ModelSerializer` crea i `PrimaryKeyRelatedField` con `queryset = Model.objects.all()`, quindi accetta qualsiasi id esistente.

## Come l'abbiamo confermata
Test temporaneo durante l'audit: insegnante A, allievo di B, POST su lezioni, pagamenti e pacchetti. Lezioni e pagamenti: 201 e riga creata nel tenant di B. Pacchetti: 400, ma per un altro bug (`lessons_remaining` obbligatorio).

## Risoluzione
`ScopedRelatedFieldsMixin` in `backend/apps/common/serializers.py` sostituisce a ogni richiesta il queryset di `student` e `package` con quelli visibili all'utente. Test di regressione `test_cross_tenant_writes.py` in lessons, payments e packages.

## Lezione per il futuro
L'autorizzazione a livello di oggetto va verificata anche sugli oggetti **referenziati nel corpo** della richiesta, non solo su quello della URL. Ogni nuovo campo di relazione scrivibile va aggiunto allo scoping e coperto da un test cross-tenant in scrittura.

## Riferimenti
- `docs/learning/concetti/isolamento-tenant-e-bola.md`
- OWASP API Security Top 10, API1:2023 Broken Object Level Authorization
