from celery import shared_task

from . import services


@shared_task
def purge_expired_tokens() -> int:
    """Daily: keep the revocation tables bounded by the refresh-token lifetime."""
    return services.purge_expired_tokens()
