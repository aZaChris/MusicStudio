# ADR-008: Promemoria delle lezioni con consegna "at most once"

- Stato: sostituito da ADR-015 (fase 3)
- Data: 2026-11-06

## Contesto

Ogni 15 minuti Celery Beat lancia un task che manda un'email ai genitori per le lezioni di circa 24 ore dopo. Il task leggeva le lezioni, inviava le email e solo alla fine segnava `reminder_sent_at`. Se due esecuzioni si sovrapponevano (worker lento, beat duplicato) o il worker si fermava a metà, lo stesso genitore poteva ricevere due email.

## Decisione

Per ogni lezione il task prima la "reclama" con un `UPDATE` condizionale:

`UPDATE lesson SET reminder_sent_at = now WHERE id = ? AND reminder_sent_at IS NULL`

e invia le email solo se l'UPDATE ha modificato una riga. PostgreSQL garantisce che solo una delle due esecuzioni concorrenti vinca. Se l'invio fallisce, l'errore viene registrato nel log e il claim non viene annullato.

## Alternative scartate

- **Invia e poi segna** (il comportamento precedente): at-least-once senza deduplica, quindi email doppie.
- **`select_for_update` su tutto il lotto**: terrebbe i lock di riga per tutto il tempo dell'invio SMTP.
- **Tabella outbox con stato per destinatario e retry**: è la soluzione corretta (at-least-once più deduplica), ma è più complessa. È prevista nella fase 3, insieme ai task idempotenti.

## Conseguenze

- Se il processo muore tra il claim e l'invio, quel promemoria è **perso**. È una scelta voluta: un promemoria mancato è meno dannoso di uno spam ripetuto. Ma è un punto debole da conoscere.
- Il claim è per lezione, non per genitore. Se l'email al primo genitore va a buon fine e quella al secondo fallisce, il secondo non riceve nulla.
