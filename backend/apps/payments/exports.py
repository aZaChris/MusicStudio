"""Esportazione CSV del registro di cassa per il commercialista (fase 8, FR-014, FR-015).

Funzioni pure: niente HTTP e niente database, ricevono righe già pronte (selectors.register_rows).
Scelte, motivate in specs/008-cash-register-receipts/research.md (R3):

- separatore `;`, UTF-8 con BOM, fine riga `\\r\\n`: Excel con impostazioni italiane spezza le
  colonne sul punto e virgola e ha bisogno del BOM per leggere le lettere accentate. È una scelta
  discutibile (a livello internazionale il separatore è la virgola);
- i campi di testo scritti da una persona (studente, motivo) vengono neutralizzati contro
  l'iniezione di formule: un valore che inizia con `=`, `+`, `-`, `@`, tab o a capo riceve un
  apostrofo davanti, così il foglio di calcolo lo mostra come testo e non lo esegue. Gli importi
  si scrivono dal tipo Decimal e non si toccano (un `-40.00` legittimo resta un numero).
"""

import csv
import datetime
import io
from collections.abc import Iterable
from decimal import Decimal
from typing import Any

COLUMNS = [
    "date",
    "receipt_number",
    "student",
    "method",
    "amount",
    "status",
    "reason",
    "reversal_of",
    "package",
    "cause",  # fase 9: manual | refund | dispute (solo sulle righe di storno)
    "provider_ref",  # id del rimborso o della contestazione di Stripe
]

_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def neutralise(value: object) -> str:
    """Testo sicuro per una cella: un valore che un foglio di calcolo eseguirebbe diventa testo."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_STARTS) else text


def _cell(column: str, value: Any) -> str:
    if isinstance(value, Decimal):
        return f"{value:.2f}"  # un numero vero, mai neutralizzato
    if isinstance(value, datetime.date):
        return value.isoformat()
    if column in ("student", "reason", "receipt_number", "method", "status"):
        return neutralise(value)
    return "" if value is None else str(value)


def write_register_csv(rows: Iterable[dict[str, Any]]) -> bytes:
    """Il registro come CSV: una riga per pagamento, intestazione in inglese come l'API."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow([_cell(column, row.get(column)) for column in COLUMNS])
    return ("﻿" + buffer.getvalue()).encode("utf-8")
