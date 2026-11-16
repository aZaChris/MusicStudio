"""PDF del registro di cassa e (più avanti) delle ricevute, con reportlab (fase 8, research R10).

Funzioni pure: ricevono dati già pronti e restituiscono i byte del PDF, senza HTTP né ORM.
Font Helvetica integrato: copre le lettere accentate italiane e il simbolo dell'euro (WinAnsi).
Il testo è nella lingua dell'utente (`it` o `en`); un solo dizionario per lingua, qui sotto.
"""

import datetime
import io
from decimal import Decimal
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

LABELS: dict[str, dict[str, str]] = {
    "en": {
        "register_title": "Cash register",
        "period": "Period",
        "from_to": "{start} to {end}",
        "method": "Method",
        "received": "Received",
        "reversed": "Reversed",
        "net": "Net",
        "total": "Total",
        "produced": "Produced on {day}",
        "not_tax": "This document is not a tax document.",
        "provider_note": "Refunds and disputes come from the payment provider (Stripe).",
        "receipt_title": "Payment receipt",
        "receipt_no": "Receipt no. {number}",
        "studio": "Studio",
        "student": "Student",
        "amount": "Amount",
        "date": "Date",
        "receipt_not_tax": "This is a payment receipt. It is not a tax document.",
        "cancelled": "CANCELLED",
        "cancelled_note": "This payment was reversed: the receipt is no longer valid.",
        "cash": "Cash",
        "bank_transfer": "Bank transfer",
        "manual_entry": "Manual entry",
        "card": "Card (online)",
    },
    "it": {
        "register_title": "Registro di cassa",
        "period": "Periodo",
        "from_to": "dal {start} al {end}",
        "method": "Metodo",
        "received": "Incassato",
        "reversed": "Stornato",
        "net": "Netto",
        "total": "Totale",
        "produced": "Prodotto il {day}",
        "not_tax": "Questo documento non è un documento fiscale.",
        "provider_note": "Rimborsi e contestazioni arrivano dal fornitore dei pagamenti (Stripe).",
        "receipt_title": "Ricevuta di pagamento",
        "receipt_no": "Ricevuta n. {number}",
        "studio": "Studio",
        "student": "Studente",
        "amount": "Importo",
        "date": "Data",
        "receipt_not_tax": "Questa è una ricevuta di pagamento. Non è un documento fiscale.",
        "cancelled": "ANNULLATA",
        "cancelled_note": "Questo pagamento è stato stornato: la ricevuta non è più valida.",
        "cash": "Contanti",
        "bank_transfer": "Bonifico",
        "manual_entry": "Inserimento manuale",
        "card": "Carta (online)",
    },
}


def labels(language: str) -> dict[str, str]:
    # Una lingua sconosciuta ricade sull'inglese, come per le email dell'account.
    return LABELS.get(language, LABELS["en"])


def _money(value: Decimal) -> str:
    return f"€ {value:,.2f}"


def _day(value: datetime.date, language: str) -> str:
    return value.strftime("%d/%m/%Y") if language == "it" else value.isoformat()


def register_pdf(
    *,
    studio_name: str,
    summary: dict[str, Any],
    produced_on: datetime.date,
    language: str = "en",
    compress: bool = True,
) -> bytes:
    """Il riepilogo del registro per un periodo: studio, periodo, totali per metodo, data.

    `compress=False` serve ai test, che così possono cercare il testo nei byte del PDF.
    """
    text = labels(language)
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    period = summary["period"]
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"{text['register_title']} — {studio_name}",
        pageCompression=1 if compress else 0,
    )
    header = [text["method"], text["received"], text["reversed"], text["net"]]
    rows = [
        [text.get(line["method"], line["method"])]
        + [_money(line[key]) for key in ("received", "reversed", "net")]
        for line in summary["by_method"]
    ]
    totals = summary["totals"]
    rows.append([text["total"]] + [_money(totals[key]) for key in ("received", "reversed", "net")])
    table = Table([header, *rows], colWidths=[60 * mm, 36 * mm, 36 * mm, 36 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
                ("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.black),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.whitesmoke]),
            ]
        )
    )
    period_text = text["from_to"].format(
        start=_day(period["from"], language), end=_day(period["to"], language)
    )
    story = [
        Paragraph(text["register_title"], styles["Title"]),
        Paragraph(f"<b>{_escape(studio_name)}</b>", styles["Heading2"]),
        Paragraph(f"{text['period']}: {period_text}", styles["Normal"]),
        Spacer(1, 8 * mm),
        table,
        Spacer(1, 10 * mm),
        Paragraph(text["produced"].format(day=_day(produced_on, language)), small),
        Paragraph(text["not_tax"], small),
        Paragraph(text["provider_note"], small),
    ]
    doc.build(story)
    return buffer.getvalue()


def _escape(value: str) -> str:
    # Paragraph interpreta un mini-HTML: i nomi con & < > non devono rompere il documento.
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def receipt_pdf(
    *,
    studio_name: str,
    student_name: str,
    amount: Decimal,
    day: datetime.date,
    method: str,
    number: str,
    language: str = "it",
    cancelled: bool = False,
    compress: bool = True,
) -> bytes:
    """La ricevuta di un pagamento: studio, studente, importo, data, metodo e numero.

    Solo questi dati (FR-029): niente coordinate bancarie, codici fiscali o dati di chi ha
    pagato. Dice chiaramente di non essere un documento fiscale; se il pagamento è stato
    stornato porta il segno "annullata", in alto e in diagonale su tutta la pagina.
    """
    text = labels(language)
    styles = getSampleStyleSheet()
    note = ParagraphStyle("note", parent=styles["Normal"], fontSize=10, textColor=colors.grey)
    alert = ParagraphStyle(
        "alert",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.red,
        fontName="Helvetica-Bold",
    )
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=25 * mm,
        rightMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
        title=f"{text['receipt_title']} {number}",
        pageCompression=1 if compress else 0,
        # Stesso input, stessi byte: senza `invariant` reportlab scrive data e id casuali nel PDF,
        # e "rigenerare dà lo stesso contenuto" (FR-027) non sarebbe verificabile.
        invariant=1,
    )
    rows = [
        [text["studio"], studio_name],
        [text["student"], student_name],
        [text["amount"], _money(amount)],
        [text["date"], _day(day, language)],
        [text["method"], text.get(method, method)],
    ]
    table = Table(
        [
            [
                Paragraph(f"<b>{label}</b>", styles["Normal"]),
                Paragraph(_escape(value), styles["Normal"]),
            ]
            for label, value in rows
        ],
        colWidths=[40 * mm, 110 * mm],
    )
    table.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.lightgrey)]))
    story: list[Any] = [
        Paragraph(text["receipt_title"], styles["Title"]),
        Paragraph(f"<b>{text['receipt_no'].format(number=number)}</b>", styles["Heading2"]),
    ]
    if cancelled:
        story += [
            Paragraph(f"{text['cancelled']} — {text['cancelled_note']}", alert),
            Spacer(1, 4 * mm),
        ]
    story += [
        Spacer(1, 6 * mm),
        table,
        Spacer(1, 12 * mm),
        Paragraph(text["receipt_not_tax"], note),
    ]

    def watermark(canvas: Any, _doc: Any) -> None:
        if not cancelled:
            return
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 90)
        canvas.setFillColor(colors.Color(1, 0, 0, alpha=0.12))
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(40)
        canvas.drawCentredString(0, 0, text["cancelled"])
        canvas.restoreState()

    doc.build(story, onFirstPage=watermark, onLaterPages=watermark)
    return buffer.getvalue()
