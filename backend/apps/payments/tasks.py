"""Task Celery dei pagamenti. Involucri sottili: logica e idempotenza vivono in services.py.

Perché un task deve poter girare due volte senza danni:
docs/learning/concetti/task-celery-idempotenti.md e ADR-016 (affidabilità di Celery).
"""

from celery import shared_task
from django.db import InterfaceError, OperationalError

from . import services
from .gateway import PaymentsUnavailable


@shared_task(
    # Riprova solo se è caduto il database (errore temporaneo), con attesa crescente:
    # 8 tentativi, al massimo 10 minuti tra l'uno e l'altro.
    autoretry_for=(OperationalError, InterfaceError),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=8,
)
def process_webhook_event(event_pk: int) -> bool:
    """Applica un evento Stripe già salvato. Due esecuzioni sono innocue (guardia processed_at)."""
    return services.process_webhook_event(event_pk)


# Riprova solo se Stripe non risponde: un errore di logica non va ritentato all'infinito.
@shared_task(autoretry_for=(PaymentsUnavailable,), retry_backoff=True, max_retries=3)
def reconcile_open_checkouts() -> int:
    """Ogni ora: risolve i tentativi il cui webhook non è mai arrivato (ADR-014).

    È la rete di sicurezza: si pianifica in config/celery.py (Celery beat).
    """
    return services.reconcile_open_checkouts()


@shared_task
def refresh_payment_accounts() -> int:
    """Ogni ora: rilegge lo stato dei conti di pagamento degli studi (fase 9, ADR-037).

    Spento con l'interruttore dei pagamenti online. Un errore su un conto non ferma gli altri
    (lo gestisce il service), quindi non serve riprovare l'intero giro.
    """
    return services.refresh_accounts()
