import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import User
from apps.students.models import ParentStudentLink, Student
from apps.studios.models import Studio, Teacher

pytestmark = pytest.mark.django_db

GOOD = "Tr0ub4dor&3-horse"


@pytest.fixture(autouse=True)
def password_from_env(monkeypatch):
    monkeypatch.setenv("ACCOUNT_PASSWORD", GOOD)


def _student(teacher: Teacher, name: str = "Giulia") -> Student:
    return Student.objects.create(
        first_name=name,
        last_name="Rossi",
        instrument="Piano",
        teacher=teacher,
        studio=teacher.studio,
    )


def test_create_teacher_alone_gets_a_personal_studio_and_a_working_password():
    call_command("create_teacher", "--email", "Maria@Example.com")

    user = User.objects.get(email="maria@example.com")
    assert user.role == User.Role.TEACHER and user.check_password(GOOD)
    teacher = Teacher.objects.get(user=user)
    assert teacher.is_owner and teacher.studio.owner_id == teacher.pk


def test_create_teacher_with_a_studio_name_makes_a_studio_owner():
    call_command("create_teacher", "--email", "owner@studio.it", "--studio-name", "Studio Verdi")

    user = User.objects.get(email="owner@studio.it")
    assert user.role == User.Role.STUDIO_OWNER
    assert Studio.objects.get(name="Studio Verdi").owner.user == user


def test_create_teacher_never_touches_an_existing_account(monkeypatch):
    call_command("create_teacher", "--email", "maria@example.com")
    monkeypatch.setenv("ACCOUNT_PASSWORD", "An0ther-Long-Pass9")

    with pytest.raises(CommandError, match="already exists"):
        call_command("create_teacher", "--email", "MARIA@example.com")

    assert User.objects.get(email="maria@example.com").check_password(GOOD)


def test_a_weak_password_is_refused_and_nothing_is_created(monkeypatch):
    monkeypatch.setenv("ACCOUNT_PASSWORD", "password")

    with pytest.raises(CommandError):
        call_command("create_teacher", "--email", "weak@example.com")

    assert not User.objects.filter(email="weak@example.com").exists()


def test_create_parent_links_the_students():
    call_command("create_teacher", "--email", "maria@example.com")
    teacher = Teacher.objects.get(user__email="maria@example.com")
    a, b = _student(teacher, "Giulia"), _student(teacher, "Marco")

    call_command(
        "create_parent",
        "--email",
        "anna@example.com",
        "--student-id",
        str(a.pk),
        "--student-id",
        str(b.pk),
    )

    user = User.objects.get(email="anna@example.com")
    assert user.role == User.Role.PARENT and user.check_password(GOOD)
    assert set(
        ParentStudentLink.objects.filter(parent__user=user).values_list("student", flat=True)
    ) == {a.pk, b.pk}


def test_create_parent_on_an_existing_parent_only_adds_links(monkeypatch):
    call_command("create_teacher", "--email", "maria@example.com")
    teacher = Teacher.objects.get(user__email="maria@example.com")
    a, b = _student(teacher, "Giulia"), _student(teacher, "Marco")
    call_command("create_parent", "--email", "anna@example.com", "--student-id", str(a.pk))
    monkeypatch.setenv("ACCOUNT_PASSWORD", "An0ther-Long-Pass9")

    call_command("create_parent", "--email", "anna@example.com", "--student-id", str(b.pk))

    user = User.objects.get(email="anna@example.com")
    assert user.check_password(GOOD)  # the password stayed
    assert ParentStudentLink.objects.filter(parent__user=user).count() == 2


def test_create_parent_refuses_a_teacher_email_and_unknown_students():
    call_command("create_teacher", "--email", "maria@example.com")
    teacher = Teacher.objects.get(user__email="maria@example.com")
    a = _student(teacher)

    with pytest.raises(CommandError, match="not a parent"):
        call_command("create_parent", "--email", "maria@example.com", "--student-id", str(a.pk))
    with pytest.raises(CommandError, match="No student"):
        call_command("create_parent", "--email", "new@example.com", "--student-id", "99999")
    assert not User.objects.filter(email="new@example.com").exists()
