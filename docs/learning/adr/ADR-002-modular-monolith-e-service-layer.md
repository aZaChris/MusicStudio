# ADR-002: Modular monolith con service layer esplicito

- Stato: accettato
- Data: 2026-11-06

## Contesto

Il backend aveva già un'app Django per dominio, ma la logica di business era sparsa. Le transizioni di stato della lezione erano metodi del modello. La dashboard faceva quattro query e un filtro Python dentro la view. Le regole di default (insegnante, pacchetto) erano in `serializer.create`. La validazione pagamento-pacchetto era duplicata tra modello e serializer. Il risultato: regole difficili da trovare, query nascoste nelle property e test possibili solo passando dall'HTTP.

## Decisione

Restiamo un **monolite modulare**: un solo progetto deployabile, un'app per dominio. Dentro ogni app:

- `services.py`: casi d'uso di scrittura. Funzioni semplici con argomenti keyword, transazioni, invarianti. Sollevano `django.core.exceptions.ValidationError`.
- `selectors.py`: letture non banali. Scoping per tenant, `select_related`, `Prefetch`, annotazioni. Restituiscono queryset.
- View e serializer sottili: validano l'input HTTP, chiamano un service o un selector, serializzano l'output.
- I modelli contengono dati, vincoli, indici e property banali.

Un exception handler DRF (`backend/apps/common/exceptions.py`) traduce la `ValidationError` di Django in una risposta 400.

## Alternative scartate

- **Fat models**: la logica nei metodi del modello. È il default di Django, ma porta a `save()` sovrascritti e property che fanno query nascoste.
- **Repository pattern**: un livello sopra l'ORM. Duplica l'ORM senza aggiungere valore in un progetto Django.
- **Microservizi**: per studi con 1-10 insegnanti, il costo operativo (rete, deploy, consistenza distribuita) non si giustifica.
- **DDD con aggregati e domain events**: troppa cerimonia per questa dimensione.

## Conseguenze

- Le regole si testano chiamando una funzione, senza client HTTP.
- Celery, admin e comandi di gestione riusano gli stessi service.
- Serve disciplina: niente logica nuova nelle view. La regola è nella constitution (Principio V) e si controlla in review.
- Le app si importano a vicenda tramite modelli, service e selector, mai tramite view.
