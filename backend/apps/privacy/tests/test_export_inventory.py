"""Ogni modello del progetto ha una risposta scritta: esportato o escluso, e perché (ADR-042).

Aggiungere un modello senza decidere fa fallire il primo test con il suo nome: l'export non può
dimenticare in silenzio dati personali nuovi (spec 010, FR-012).
"""

import pytest
from django.apps import apps

from apps.privacy.inventory import INVENTORY
from apps.privacy.tests.test_export_completeness import full_family_exports


def project_models() -> set[str]:
    return {m._meta.label for m in apps.get_models() if m.__module__.startswith("apps.")}


def test_every_project_model_is_in_the_inventory():
    missing = project_models() - set(INVENTORY)
    assert not missing, f"Add these models to apps/privacy/inventory.py: {sorted(missing)}"


def test_the_inventory_names_only_real_models():
    assert set(INVENTORY) <= project_models()


def test_every_exclusion_has_a_real_reason():
    for label, (kind, text) in INVENTORY.items():
        assert kind in ("exported", "excluded"), label
        if kind == "excluded":
            assert len(text) >= 10, f"{label}: write why it is excluded"


@pytest.mark.django_db
def test_every_exported_key_is_really_in_the_export():
    keys = set()
    for export in full_family_exports():
        keys |= set(export)
    for label, (kind, key) in INVENTORY.items():
        if kind == "exported":
            assert key in keys, f"{label} says it is exported under '{key}', which is not there"
