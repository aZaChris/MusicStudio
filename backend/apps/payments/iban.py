"""Controllo formale di un IBAN con la sola libreria standard (fase 8, research R2).

Due controlli: la forma (due lettere di paese, due cifre di controllo, da 11 a 30 caratteri
alfanumerici) e il checksum mod-97 dello standard ISO 13616. Non c'è una tabella delle lunghezze
per paese: il checksum intercetta quasi tutti gli errori di battitura, e la tabella sarebbe dati
da tenere aggiornati. Non verifica che il conto esista: nessuna banca viene interrogata.
Stessa scelta del TOTP (ADR-029): poche righe e un test con numeri noti, invece di una dipendenza.
"""

import re

_SHAPE = re.compile(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$")


def normalise(value: str) -> str:
    """Senza spazi e in maiuscolo: la forma in cui si salva e si controlla."""
    return "".join(value.split()).upper()


def is_valid(value: str) -> bool:
    iban = normalise(value)
    if not _SHAPE.match(iban):
        return False
    # Si sposta l'inizio (paese e cifre di controllo) in fondo e si trasformano le lettere in
    # numeri (A=10 ... Z=35): l'intero risultante, diviso per 97, deve dare resto 1.
    rearranged = iban[4:] + iban[:4]
    digits = "".join(str(int(char, 36)) for char in rearranged)
    return int(digits) % 97 == 1
