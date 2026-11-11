from celery import shared_task

from apps.accounts import emails
from apps.students.models import Student


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def notify_parent_left(student_id: int) -> None:
    """Tell the teacher that one of a child's two parents closed their account. The parent
    is not named: their data is gone."""
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
