"""Factory condivise per i test: le usano le suite di più app, non è un modulo di test."""

import datetime

import factory
from django.utils import timezone

from apps.accounts.models import User
from apps.lessons.models import Lesson
from apps.lessons.selectors import week_bounds
from apps.packages.models import Package
from apps.payments.models import Payment, StudioPaymentAccount
from apps.students.models import ParentAccount, ParentStudentLink, Student
from apps.studios.models import Studio, Teacher


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    role = User.Role.TEACHER
    email_verified = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "password123")
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user


class StudioFactory(factory.django.DjangoModelFactory[Studio]):
    class Meta:
        model = Studio

    name = factory.Sequence(lambda n: f"Studio {n}")


class StudioPaymentAccountFactory(factory.django.DjangoModelFactory[StudioPaymentAccount]):
    # Il conto Stripe di uno studio (fase 9). Per default è attivo: la maggior parte dei test
    # sui pagamenti online parte da un conto che può incassare.
    class Meta:
        model = StudioPaymentAccount

    studio = factory.SubFactory(StudioFactory)
    stripe_account_id = factory.Sequence(lambda n: f"acct_test_{n + 100}")
    state = StudioPaymentAccount.State.ACTIVE


class TeacherFactory(factory.django.DjangoModelFactory[Teacher]):
    class Meta:
        model = Teacher

    user = factory.SubFactory(UserFactory, role=User.Role.TEACHER)
    studio = factory.SubFactory(StudioFactory)  # ogni insegnante appartiene a uno studio (ADR-010)
    is_owner = False


class StudentFactory(factory.django.DjangoModelFactory[Student]):
    class Meta:
        model = Student

    first_name = factory.Sequence(lambda n: f"Student{n}")
    last_name = "Test"
    instrument = "Piano"
    teacher = factory.SubFactory(TeacherFactory)
    studio = factory.LazyAttribute(lambda o: o.teacher.studio)


class PackageFactory(factory.django.DjangoModelFactory[Package]):
    class Meta:
        model = Package

    student = factory.SubFactory(StudentFactory)
    total_lessons = 8
    lessons_remaining = 8
    purchase_date = factory.LazyFunction(datetime.date.today)
    price = "120.00"


class PaymentFactory(factory.django.DjangoModelFactory[Payment]):
    # Pagamento già pagato in contanti, di oggi: il caso più comune nei test del registro.
    class Meta:
        model = Payment

    student = factory.SubFactory(StudentFactory)
    amount = "40.00"
    date = factory.LazyFunction(datetime.date.today)
    method = Payment.Method.CASH
    status = Payment.Status.PAID


def _factory_start(n: int) -> datetime.datetime:
    """Inizio dell'n-esima lezione della factory: a 31 minuti l'una dall'altra, ciclo di ~20 ore.

    La distanza evita che lezioni dello stesso insegnante o studente urtino i vincoli di
    sovrapposizione. L'elenco delle lezioni mostra di default la settimana corrente, quindi un
    inizio oltre la fine della settimana (domenica sera, Europe/Rome) torna indietro di una
    settimana: altrimenti l'elenco sarebbe vuoto e i test fallirebbero solo la domenica sera.
    """
    now = datetime.datetime.now(datetime.UTC)
    start = now + datetime.timedelta(hours=1, minutes=31 * (n % 40))
    _, week_end = week_bounds(timezone.localdate())
    return start - datetime.timedelta(days=7) if start >= week_end else start


class LessonFactory(factory.django.DjangoModelFactory[Lesson]):
    class Meta:
        model = Lesson

    student = factory.SubFactory(StudentFactory)
    teacher = factory.LazyAttribute(lambda o: o.student.teacher)
    package = None
    start_time = factory.Sequence(_factory_start)
    end_time = factory.LazyAttribute(lambda o: o.start_time + datetime.timedelta(minutes=30))


class ParentAccountFactory(factory.django.DjangoModelFactory[ParentAccount]):
    class Meta:
        model = ParentAccount

    user = factory.SubFactory(UserFactory, role=User.Role.PARENT)


def link_parent_to_student(parent: ParentAccount, student: Student) -> ParentStudentLink:
    return ParentStudentLink.objects.create(parent=parent, student=student)


def make_student_account(student: Student) -> User:
    """Dà a uno studente adulto un account proprio, in sola lettura (fase 7)."""
    user = UserFactory(role=User.Role.STUDENT)
    student.is_adult = True
    student.user = user
    student.save(update_fields=["is_adult", "user"])
    return user


def make_reversal(payment: Payment, **overrides: object) -> Payment:
    # Crea direttamente la riga di storno di un pagamento, senza passare dal service: serve ai
    # test che partono da un registro già corretto.
    fields: dict[str, object] = {
        "student": payment.student,
        "package": payment.package,
        "amount": payment.amount,
        "date": datetime.date.today(),
        "method": payment.method,
        "status": Payment.Status.REVERSAL,
        "reversal_of": payment,
    }
    return Payment.objects.create(**{**fields, **overrides})
