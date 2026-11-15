"""Receipt PDF: the right data, the non-fiscal sentence, the cancelled mark, nothing else."""

import datetime
from decimal import Decimal

import pytest

from apps.payments.pdf import receipt_pdf


def _pdf(**overrides) -> bytes:
    fields = {
        "studio_name": "Studio Armonia",
        "student_name": "Giulia Rossi",
        "amount": Decimal("40.00"),
        "day": datetime.date(2026, 11, 3),
        "method": "cash",
        "number": "2026-0007",
        "language": "en",
        "compress": False,
        **overrides,
    }
    return receipt_pdf(**fields)


def test_english_receipt_has_every_field_and_the_non_fiscal_sentence():
    data = _pdf()

    assert data.startswith(b"%PDF")
    for text in (
        b"Payment receipt",
        b"Receipt no. 2026-0007",
        b"Studio Armonia",
        b"Giulia Rossi",
        b"40.00",
        b"2026-11-03",
        b"Cash",
        b"It is not a tax document.",
    ):
        assert text in data, text
    assert b"CANCELLED" not in data


def test_italian_receipt_uses_italian_labels_and_date():
    data = _pdf(language="it", method="bank_transfer")

    for text in (
        b"Ricevuta di pagamento",
        b"Ricevuta n. 2026-0007",
        b"03/11/2026",
        b"Bonifico",
        b"Studente",
    ):
        assert text in data, text
    assert b"fiscale" in data and b"ANNULLATA" not in data


@pytest.mark.parametrize(("language", "mark"), [("en", b"CANCELLED"), ("it", b"ANNULLATA")])
def test_a_cancelled_receipt_carries_a_clear_mark(language, mark):
    data = _pdf(cancelled=True, language=language)

    assert data.count(mark) >= 2  # the banner at the top and the diagonal watermark


def test_it_contains_nothing_beyond_the_five_fields_and_the_number():
    data = _pdf()

    for forbidden in (b"IBAN", b"iban", b"VAT", b"P.IVA", b"Partita", b"fiscal code", b"payer"):
        assert forbidden not in data, forbidden


def test_names_with_markup_characters_and_accents_do_not_break_it():
    data = _pdf(student_name="Zoë <Müller> & Co", studio_name="Rock & Roll")

    assert data.startswith(b"%PDF") and b"&amp;" not in data
    # The accents are WinAnsi octal escapes in the stream (e-diaeresis 353, u-diaeresis 374).
    assert b"Zo\\353" in data and b"M\\374ller" in data


def test_an_unknown_language_falls_back_to_english():
    assert b"Payment receipt" in _pdf(language="fr")


def test_the_default_compressed_output_is_a_valid_pdf():
    assert _pdf(compress=True).startswith(b"%PDF")
