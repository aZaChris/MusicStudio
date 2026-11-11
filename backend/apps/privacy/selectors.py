"""The family export (GDPR access/portability): everything held about one account.

Scope is decided here by who the account is, never by an id from the request: a parent gets
the children linked to them, an adult student gets their own record.
"""

from typing import Any

from django.db.models import Prefetch, QuerySet

from apps.accounts.models import User
from apps.lessons.models import Lesson
from apps.packages.models import Package
from apps.payments.models import Payment
from apps.students.models import Student

from .models import ConsentRecord


def students_of(user: User) -> QuerySet[Student]:
    if user.role == User.Role.STUDENT:
        return Student.objects.filter(user=user)
    return Student.objects.filter(parent_accounts__user=user)


def build_export(user: User) -> dict[str, Any]:
    children = list(
        students_of(user)
        .select_related("studio")
        .prefetch_related(
            Prefetch("lessons", queryset=Lesson.objects.order_by("start_time")),
            Prefetch("packages", queryset=Package.objects.order_by("purchase_date", "id")),
            Prefetch("payments", queryset=Payment.objects.order_by("date", "id")),
        )
        .order_by("id")
    )
    consents = ConsentRecord.objects.filter(parent__user=user).prefetch_related("students")
    return {
        "account": {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "preferred_language": user.preferred_language,
            "created_at": user.date_joined,
            "terms_accepted_at": user.terms_accepted_at,
        },
        "children": [
            {
                "id": s.pk,
                "first_name": s.first_name,
                "last_name": s.last_name,
                "instrument": s.instrument,
                "studio": s.studio.name,
                "is_active": s.is_active,
                "lessons": [
                    {
                        "id": lesson.pk,
                        "start_time": lesson.start_time,
                        "end_time": lesson.end_time,
                        "status": lesson.status,
                        "notes": lesson.notes,
                    }
                    for lesson in s.lessons.all()
                ],
                "packages": [
                    {
                        "id": p.pk,
                        "total_lessons": p.total_lessons,
                        "lessons_remaining": p.lessons_remaining,
                        "purchase_date": p.purchase_date,
                        "expiry_date": p.expiry_date,
                        "price": p.price,
                    }
                    for p in s.packages.all()
                ],
                "payments": [
                    {
                        "id": pay.pk,
                        "amount": pay.amount,
                        "date": pay.date,
                        "method": pay.method,
                        "status": pay.status,
                    }
                    for pay in s.payments.all()
                ],
            }
            for s in children
        ],
        "consents": [
            {
                "id": c.pk,
                "notice_version": c.notice_version,
                "given_at": c.given_at,
                "withdrawn_at": c.withdrawn_at,
                "children": [s.pk for s in c.students.all()],
            }
            for c in consents
        ],
    }
