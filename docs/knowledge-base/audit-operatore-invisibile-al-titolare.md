# Le azioni dell'operatore non comparivano nell'audit del titolare

## Sintomo

Il quickstart della fase 7 dice: dopo `manage.py unlock_account <email>` lo sblocco "compare nella vista audit". Nel giro di verifica (server vero, database usa e getta) il titolare vedeva blocco, login e MFA, ma non lo sblocco. Stesso problema per `reset_mfa`. I test passavano.

## Causa radice

La vista audit del titolare mostra le voci con lo `studio_id` del suo studio, più quelle senza studio il cui **autore** è un insegnante dello studio. I due comandi registravano la voce con `target=user` e basta: l'operatore non ha un account, quindi niente autore, e nessuno aveva passato lo studio. Una voce senza studio e senza autore non appartiene a nessuno studio: esiste nel database, ma nessun titolare la vede.

I test controllavano solo che la voce esistesse (`count() == 1`), non che fosse visibile a chi deve leggerla.

## Come l'abbiamo confermata

Interrogando `audit_auditentry` dopo il giro: `account.unlock_by_operator` aveva `studio_id` vuoto e `actor` vuoto, unica tra le voci dell'insegnante a non avere né l'uno né l'altro.

## Risoluzione

I due comandi passano `studio_id=_studio_id(user)`, lo stesso helper che usano già i service degli account. I test ora controllano lo studio della voce. Rilanciato il giro: lo sblocco compare.

## Lezione per il futuro

Per un log letto per studio, "la voce esiste" non basta: va provato che la vede chi deve vederla. Ogni azione senza autore (comandi, job) deve dire esplicitamente a quale studio appartiene.

## Riferimenti

- `backend/apps/accounts/management/commands/unlock_account.py`, `reset_mfa.py`
- `backend/apps/audit/selectors.py` (`entries_for_owner`)
- `backend/apps/accounts/tests/test_operator_commands.py`
- ADR-031 (audit log dai service)
