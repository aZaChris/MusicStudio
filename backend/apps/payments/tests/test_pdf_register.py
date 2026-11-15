"""Register PDF: a real PDF with the studio, the period, the totals and the production date."""

import datetime
from decimal import Decimal

import pytest

from apps.payments.pdf import register_pdf

SUMMARY = {
    "period": {"from": datetime.date(2026, 11, 1), "to": datetime.date(2026, 11, 30)},
    "totals": {
        "received": Decimal("140.00"),
        "reversed": Decimal("40.00"),
        "net": Decimal("100.00"),
    },
    "by_method": [
        {
            "method": "cash",
            "received": Decimal("100.00"),
            "reversed": Decimal("40.00"),
            "net": Decimal("60.00"),
        },
        {
            "method": "bank_transfer",
            "received": Decimal("40.00"),
            "reversed": Decimal("0.00"),
            "net": Decimal("40.00"),
        },
        {
            "method": "manual_entry",
            "received": Decimal("0.00"),
            "reversed": Decimal("0.00"),
            "net": Decimal("0.00"),
        },
        {
            "method": "card",
            "received": Decimal("0.00"),
            "reversed": Decimal("0.00"),
            "net": Decimal("0.00"),
        },
    ],
    "counts": {"paid": 2, "pending": 0, "overdue": 0, "reversal": 1},
}


def _pdf(**kw) -> bytes:
    return register_pdf(
        studio_name=kw.pop("studio_name", "Studio Armonia"),
        summary=SUMMARY,
        produced_on=datetime.date(2026, 12, 3),
        compress=False,
        **kw,
    )


def test_it_is_a_pdf_with_the_requested_content_in_english():
    data = _pdf(language="en")

    assert data.startswith(b"%PDF")
    for text in (
        b"Cash register",
        b"Studio Armonia",
        b"2026-11-01 to 2026-11-30",
        b"Bank transfer",
        b"100.00",
        b"140.00",
        b"Produced on 2026-12-03",
        b"not a tax document",
    ):
        assert text in data, text


def test_italian_labels_dates_and_accents():
    data = _pdf(language="it")

    assert b"Registro di cassa" in data
    assert b"dal 01/11/2026 al 30/11/2026" in data
    assert b"Prodotto il 03/12/2026" in data
    # "non è un documento fiscale": the accent is WinAnsi 0xE8 (written as an octal escape)
    assert b"non \\350 un documento fiscale" in data or "non è un".encode("cp1252") in data


def test_a_studio_name_with_markup_characters_does_not_break_the_document():
    data = _pdf(studio_name="Rock & Roll <Academy>")

    assert data.startswith(b"%PDF") and b"Rock &amp;" not in data
    assert b"Rock & Roll <Academy>" in data


@pytest.mark.parametrize("language", ["en", "it", "fr"])
def test_every_language_renders_and_unknown_ones_fall_back(language):
    assert _pdf(language=language).startswith(b"%PDF")


def test_the_default_compressed_output_is_a_valid_pdf():
    full = register_pdf(
        studio_name="S", summary=SUMMARY, produced_on=datetime.date(2026, 12, 3), compress=True
    )
    assert full.startswith(b"%PDF")
