# Un throttle senza tasso configurato lascia passare tutto, in silenzio

## Sintomo

Scrivendo i test delle esportazioni del registro di cassa (fase 8) ogni richiesta rispondeva 200, anche dopo decine di chiamate dello stesso utente. Le esportazioni hanno un limite di frequenza dedicato, lo scope `register_export`. Nessun errore, nessun avviso: il limite semplicemente non c'era.

## Causa radice

Il progetto usa throttle che "falliscono aperti" (`apps/common/throttling.py`): se la cache non risponde, la richiesta passa e l'errore si scrive nei log. La scelta serve a non buttare giù l'API quando Redis è giù (ADR-017).

Il `ScopedRateThrottle` di DRF legge il tasso dello scope dentro `allow_request`, non alla creazione. Se lo scope non ha un tasso nei settings, DRF solleva `ImproperlyConfigured`, e il nostro `FailOpenMixin` lo intercetta come qualunque altro errore e lascia passare la richiesta. Uno scope scritto sulla view ma dimenticato nei settings è quindi un limite che non esiste, senza nessun segnale.

Nei settings di test (`config/settings/test.py`) i tassi sono ridefiniti a mano e `register_export` non c'era.

## Come l'abbiamo confermata

I test delle esportazioni passavano con 200 senza che lo scope avesse un tasso, e non c'era nessun errore da nessuna parte. Il primo test di limite che ho scritto non vedeva mai un 429 finché non gli ho iniettato i tassi a mano. Dopo aver aggiunto `"register_export": "5/min"` ai settings di test, la sesta richiesta dà 429. Ho dedotto la causa dal codice di DRF (il tasso si legge in `allow_request`) e dal `FailOpenMixin`; non ho riprodotto il silenzio con un test dedicato.

## Risoluzione

Il tasso è nei settings di test (`5/min`) e in quelli base (`THROTTLE_REGISTER_EXPORT`, predefinito `20/hour`, documentato in `.env.example`). Un test (`test_the_export_throttle_scope_is_configured_in_production_settings`) controlla che lo scope esista nei settings di produzione, e un altro prova che la sesta richiesta riceva 429 e che un altro utente abbia un contatore proprio.

## Lezione per il futuro

Un meccanismo che fallisce aperto nasconde anche i propri errori di configurazione. Ogni scope nuovo di throttle va accompagnato da un test che ne provi il 429, altrimenti non si sa se esiste. L'idea generale vale per ogni "fail open": decidere cosa lasciar passare quando l'infrastruttura è giù è una scelta, ma non deve valere anche per un errore di battitura nella configurazione.

## Riferimenti

- `backend/apps/common/throttling.py` (`FailOpenMixin`)
- `backend/config/settings/base.py`, `backend/config/settings/test.py` (`DEFAULT_THROTTLE_RATES`)
- `backend/apps/payments/tests/test_register_export.py`
- ADR-017, `redis-giu-e-throttling.md`
