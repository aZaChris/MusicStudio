import pytest
from django.core.management import CommandError, call_command

from apps.accounts.models import MfaDevice
from apps.audit.models import AuditEntry
from apps.common.factories import TeacherFactory

pytestmark = pytest.mark.django_db


def test_unlock_account_clears_the_lock_and_is_audited():
    user = TeacherFactory().user
    user.failed_logins, user.lock_level = 3, 2
    user.locked_until = user.date_joined
    user.save()

    call_command("unlock_account", user.email.upper())

    user.refresh_from_db()
    assert (user.failed_logins, user.lock_level, user.locked_until) == (0, 0, None)
    # The studio is set, so the owner's audit view shows it (the operator has no account).
    entry = AuditEntry.objects.get(action="account.unlock_by_operator")
    assert entry.studio_id == user.teacher.studio_id


def test_reset_mfa_removes_the_device_and_is_audited():
    user = TeacherFactory().user
    MfaDevice.objects.create(user=user, secret="JBSWY3DPEHPK3PXP", confirmed_at=user.date_joined)

    call_command("reset_mfa", user.email)

    assert not MfaDevice.objects.exists()
    entry = AuditEntry.objects.get(action="mfa.reset_by_operator")
    assert entry.studio_id == user.teacher.studio_id
    with pytest.raises(CommandError):
        call_command("reset_mfa", user.email)  # nothing left to reset


def test_unknown_account_is_an_error():
    for name in ("unlock_account", "reset_mfa"):
        with pytest.raises(CommandError):
            call_command(name, "nobody@example.com")
