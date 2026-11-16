"""Ogni chiamata a Stripe passa dal gateway, e la piattaforma non prende commissioni (fase 9).

Due guardie sul sorgente: nessun modulo importa `stripe` fuori da gateway.py (ADR-013), e nessun
parametro delle richieste può chiedere una commissione o un trasferimento verso la piattaforma
(ADR-037: i soldi vanno al conto dello studio, MusicStudio non ne tocca).
"""

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
FORBIDDEN_KEYS = {
    "application_fee_amount",
    "application_fee_percent",
    "on_behalf_of",
    "transfer_data",
}


def _sources():
    for root in ("apps", "config"):
        for path in sorted((BACKEND / root).rglob("*.py")):
            relative = path.relative_to(BACKEND).as_posix()
            if "/tests/" in f"/{relative}" or "/migrations/" in f"/{relative}":
                continue
            yield relative, ast.parse(path.read_text())


def test_only_the_gateway_imports_stripe():
    importers = set()
    for relative, tree in _sources():
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and any(
                a.name.split(".")[0] == "stripe" for a in node.names
            ):
                importers.add(relative)
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "stripe":
                importers.add(relative)

    assert importers == {"apps/payments/gateway.py"}, importers


def test_no_request_can_ask_for_a_fee_or_a_transfer_to_the_platform():
    offenders = []
    for relative, tree in _sources():
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                keys = {k.value for k in node.keys if isinstance(k, ast.Constant)}
                if keys & FORBIDDEN_KEYS:
                    offenders.append((relative, sorted(keys & FORBIDDEN_KEYS)))
            if isinstance(node, ast.keyword) and node.arg in FORBIDDEN_KEYS:
                offenders.append((relative, [node.arg]))

    assert offenders == [], f"A fee or transfer parameter appeared: {offenders}"


def test_the_guard_itself_sees_a_violation():
    tree = ast.parse("params = {'payment_intent_data': 1, 'application_fee_amount': 5}")
    dicts = [n for n in ast.walk(tree) if isinstance(n, ast.Dict)]
    assert {k.value for k in dicts[0].keys if isinstance(k, ast.Constant)} & FORBIDDEN_KEYS
