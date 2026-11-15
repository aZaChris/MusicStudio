"""Task Celery della privacy: avviso agli insegnanti e conservazione notturna (ADR-032)."""

from celery import shared_task

from apps.accounts import emails
from apps.students.models import Student


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def notify_parent_left(student_id: int) -> None:
    # Avvisa l'insegnante che uno dei due genitori di un allievo ha chiuso l'account. Il genitore
    # non è nominato: i suoi dati non ci sono più. Si riprova se la posta è giù (OSError).
    student = Student.objects.select_related("teacher__user").filter(pk=student_id).first()
    if student is None:
        return
    teacher_user = student.teacher.user
    emails.send(
        "parent_left",
        to=teacher_user.email,
        language=teacher_user.preferred_language,
        context={"student_name": student.full_name, "first_name": teacher_user.first_name},
        log_id=teacher_user.pk,
    )


@shared_task
def run_retention() -> dict[str, int]:
    # Ogni notte: anonimizza gli studenti archiviati da tempo e cancella i dati scaduti.
    # Importa `services` qui dentro per evitare un import circolare con le notifiche.
    from . import services

    return services.run_retention()
