"""CSV export: round trip, and nothing a spreadsheet could run as a formula (FR-015)."""

import csv
import datetime
import io
from decimal import Decimal

import pytest

from apps.payments.exports import COLUMNS, neutralise, write_register_csv


def _read(data: bytes) -> list[dict[str, str]]:
    text = data.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text), delimiter=";"))


def _row(**overrides):
    return {
        "date": datetime.date(2026, 11, 3),
        "receipt_number": "",
        "student": "Giulia Rossi",
        "method": "cash",
        "amount": Decimal("40.00"),
        "status": "paid",
        "reason": "",
        "reversal_of": "",
        "package": 7,
        **overrides,
    }


def test_header_bom_separator_and_line_ends():
    data = write_register_csv([_row()])

    assert data.startswith("﻿".encode())  # BOM so Excel reads the accents
    first_line = data.decode("utf-8-sig").split("\r\n")[0]
    assert first_line == ";".join(COLUMNS)
    assert data.endswith(b"\r\n")


def test_values_round_trip_with_two_decimals_and_iso_dates():
    rows = _read(write_register_csv([_row(), _row(amount=Decimal("-40"), status="reversal")]))

    assert rows[0]["date"] == "2026-11-03" and rows[0]["amount"] == "40.00"
    assert rows[1]["amount"] == "-40.00"  # a legitimate negative number is not neutralised
    assert rows[0]["package"] == "7"


@pytest.mark.parametrize(
    "name",
    [
        "Zoë Müller-Çelik",  # accents
        "O'Brien, Mary",  # comma and apostrophe
        'Say "hi" to Ann',  # quotes
        "a;b;c",  # the separator itself
        "line one\nline two",  # newline inside a cell
        "x" * 500,  # very long
    ],
)
def test_awkward_names_survive_the_round_trip(name):
    rows = _read(write_register_csv([_row(student=name)]))

    assert rows[0]["student"] == name


@pytest.mark.parametrize(
    "value", ["=SUM(A1)", "+1", "-1", "@cmd", "\t=1", "\r=1", "=cmd|' /C calc'!A0"]
)
def test_text_that_looks_like_a_formula_is_neutralised(value):
    rows = _read(write_register_csv([_row(student=value, reason=value)]))

    assert rows[0]["student"] == "'" + value and rows[0]["reason"] == "'" + value


def test_neutralise_leaves_ordinary_text_alone():
    assert neutralise("Giulia Rossi") == "Giulia Rossi"
    assert neutralise("") == "" and neutralise(None) == ""
    assert neutralise("a=b") == "a=b"  # only a leading character matters
