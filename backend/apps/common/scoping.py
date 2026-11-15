"""Ambito del tenant: l'unico punto di passaggio obbligato per il Principio I della constitution.

Lo studio è il tenant (ADR-010). Ogni queryset che restituisce o accetta dati di un tenant si
filtra qui a partire dal `TenantContext` della richiesta, sia per le letture (queryset delle
view) sia per le scritture (queryset dei campi relazionali, vedi `apps/common/serializers.py`):

- titolare: tutto ciò il cui studio è lo studio del titolare;
- insegnante: tutto ciò che è collegato all'insegnante (appartiene a un solo studio);
- genitore: tutto ciò che riguarda i figli collegati (possono essere in studi diversi);
- studente (adulto, sola lettura): il proprio record e ciò che ne dipende;
- chiunque altro: niente.

Ogni modello dichiara una volta sola come arrivare a studio / insegnante / genitore
(`TenantPaths`). Spiegazione: docs/learning/concetti/multi-tenancy.md e
docs/learning/concetti/isolamento-tenant-e-bola.md.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db.models import Model, QuerySet

from .tenancy import TenantContext

if TYPE_CHECKING:
    from apps.packages.models import Package
    from apps.students.models import Student


@dataclass(frozen=True)
class TenantPaths:
    """Percorsi ORM da un modello al suo studio, insegnante, account genitore e studente."""

    studio: str
    teacher: str
    parent: str
    student: str


STUDENT_PATHS = TenantPaths(
    studio="studio", teacher="teacher", parent="parent_accounts", student="id"
)
# Una lezione appartiene all'insegnante che la tiene (resta tale se lo studente viene riassegnato).
LESSON_PATHS = TenantPaths(
    studio="student__studio",
    teacher="teacher",
    parent="student__parent_accounts",
    student="student",
)
# Pacchetti e pagamenti seguono l'insegnante attuale dello studente.
STUDENT_CHILD_PATHS = TenantPaths(
    studio="student__studio",
    teacher="student__teacher",
    parent="student__parent_accounts",
    student="student",
)


def scope[M: Model](qs: QuerySet[M], ctx: TenantContext, paths: TenantPaths) -> QuerySet[M]:
    # Il ruolo decide il filtro. L'ordine non è casuale: un ruolo sconosciuto cade nell'ultimo
    # ramo e non vede nulla (qs.none()), non tutto.
    if ctx.is_owner:
        return qs.filter(**{paths.studio: ctx.studio_id})
    if ctx.is_teacher:
        return qs.filter(**{paths.teacher: ctx.teacher_id})
    if ctx.is_parent:
        # Solo questo percorso attraversa un many-to-many, che può duplicare le righe.
        return qs.filter(**{paths.parent: ctx.parent_id}).distinct()
    if ctx.is_student:
        return qs.filter(**{paths.student: ctx.student_id})
    return qs.none()


def students_visible_to(ctx: TenantContext) -> "QuerySet[Student]":
    from apps.students.models import Student

    return scope(Student.objects.all(), ctx, STUDENT_PATHS)


def packages_visible_to(ctx: TenantContext) -> "QuerySet[Package]":
    from apps.packages.models import Package

    return scope(Package.objects.all(), ctx, STUDENT_CHILD_PATHS)
