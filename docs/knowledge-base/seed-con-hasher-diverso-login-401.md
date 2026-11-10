# KB: Nel load test tutti i login rispondevano 401

## Sintomo
Primo run di Locust (fase 4): ogni `POST /auth/token/` rispondeva 401, anche con la password giusta.

## Causa radice
I dati del load test erano stati creati con `seed_loadtest` usando i **settings di test**, che salvano le password con l'hasher MD5 (veloce, solo per i test). Il server girava con i **settings di produzione**, che accettano solo PBKDF2: gli hash MD5 non venivano riconosciuti.

## Come l'abbiamo confermata
Rigenerando le password con i settings del server, il login ha risposto 200.

## Risoluzione
Password rigenerate con gli stessi settings del server; la regola è scritta nel locustfile, nel report del load test e in `CLAUDE.md`.

## Lezione per il futuro
I dati di prova vanno creati con gli stessi settings dell'ambiente in cui verranno usati. Ciò che dipende dalla configurazione, come gli hash delle password, non si sposta tra ambienti.

## Riferimenti
- `backend/loadtest/locustfile.py`
- `docs/loadtest/2026-11-09/README.md`
