# KB: Celery scriveva il token d'invito nei log

## Sintomo
Il test che esegue registrazione, reset password, MFA e inviti con tutti i log catturati ha fallito: il token di un invito compariva in un record di log, nella riga "Task apps.accounts.tasks.send_invitation_email[...] succeeded". Nessuno se n'era accorto leggendo il codice.

## Causa radice
Quando un task finisce, Celery scrive una riga di log e allega i dati del task in un campo `data`, compresi gli argomenti (`args`, `kwargs`). Il nostro `JsonFormatter` stampa come campo di primo livello ogni valore passato con `extra={...}`, quindi in produzione gli argomenti sarebbero finiti nel log JSON. Per `send_invitation_email` l'argomento è il token in chiaro. Chi legge i log (o Sentry) avrebbe potuto usare il link prima dell'invitato.

## Come l'abbiamo confermata
Il test `config/tests/test_no_pii_in_logs.py` raccoglie tutti i record con `caplog` e cerca ogni valore digitato o spedito (email, nomi, password, token, codici). Ha trovato il token dentro `record.data["args"]`, non nel messaggio.

## Risoluzione
Un filtro, `TaskArgsFilter` in `backend/apps/common/logging.py`, toglie `args` e `kwargs` dal campo `data`. È agganciato al logger `celery.app.trace` in `LOGGING`, quindi vale per ogni handler. Un test unitario copre il filtro.

## Lezione per il futuro
Guardare solo il messaggio di un log non basta: i campi `extra` finiscono nel JSON. E un test che cerca i valori sensibili nei record trova perdite che nessuna revisione del codice vede. Se un task riceve un segreto come argomento, va pensato a come difendere anche i log.

## Riferimenti
- `docs/learning/adr/ADR-027-principi-sicurezza-e-privacy.md` (principio X)
- `backend/apps/common/logging.py`, `backend/config/settings/base.py`
