"""Guard for "a paid entry is final" (FR-001, research R6).

The rule lives in the services. `QuerySet.update()` and `QuerySet.delete()` skip model methods,
so any code that writes payments in bulk could bypass it. This test reads the source of every
non-test module and fails when a *new* place calls update, delete or bulk_update on a queryset
that starts from `Payment`. Whoever adds one has to decide, here, whether it is legitimate.
"""

import ast
from pathlib import Path

APPS = Path(__file__).resolve().parents[2]
WRITES = {"update", "delete", "bulk_update"}

# (file relative to apps/, function) -> why a bulk write on payments is legitimate there.
ALLOWED = {
    # Retention: payments older than 10 years are deleted in bulk by the nightly job (ADR-034).
    # It is the one deliberate exception: a closed accounting period, not an edit of live data.
    ("privacy/services.py", "run_retention"),
}


def _chain_starts_at_payment(node: ast.AST) -> bool:
    """True for `Payment.objects.filter(...).update(...)` and similar chains."""
    while True:
        if isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Attribute):
            node = node.value
        else:
            return isinstance(node, ast.Name) and node.id == "Payment"


def _bulk_payment_writes() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for path in sorted(APPS.rglob("*.py")):
        relative = path.relative_to(APPS).as_posix()
        if "/tests/" in f"/{relative}" or "/migrations/" in f"/{relative}":
            continue
        if relative == "common/factories.py":
            continue
        tree = ast.parse(path.read_text())
        for function in ast.walk(tree):
            if not isinstance(function, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for node in ast.walk(function):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in WRITES
                    and _chain_starts_at_payment(node.func.value)
                ):
                    found.add((relative, function.name))
    return found


def test_only_the_retention_job_writes_payments_in_bulk():
    found = _bulk_payment_writes()

    assert found == ALLOWED, (
        "Bulk writes on Payment found outside the allowed list. A paid entry is final: "
        f"corrections are reversals. New places: {found - ALLOWED}. "
        f"Allowed places that disappeared: {ALLOWED - found}."
    )


def test_the_guard_itself_sees_a_violation():
    tree = ast.parse("def f():\n    Payment.objects.filter(status='paid').update(amount=1)\n")
    call = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "update"
    )
    assert _chain_starts_at_payment(call.func.value)
    harmless = ast.parse("def f():\n    Lesson.objects.filter(pk=1).update(notes='')\n")
    other = next(
        n
        for n in ast.walk(harmless)
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "update"
    )
    assert not _chain_starts_at_payment(other.func.value)
