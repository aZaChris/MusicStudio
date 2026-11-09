# Registro delle prove di ripristino

Ogni prova di ripristino (restore drill) va registrata qui. Un backup che non è mai stato ripristinato non è una prova che i dati si possano recuperare. La procedura è nello script `scripts/restore-drill.sh` e nella sezione "Ripristino del database" del runbook.

## 2026-11-09 — prova locale su dump realistico

- **Chi**: Claude Code, durante la fase 4.
- **Dove**: computer di sviluppo (WSL2, AMD Ryzen 5 PRO 3500U, 8 thread, circa 2,7 GB di RAM assegnati a WSL), PostgreSQL 16.15. Senza Docker.
- **Sorgente**: un database creato con `manage.py seed_loadtest` (10 studi, 50 insegnanti, 1.500 allievi, 1.500 genitori, 78.000 lezioni).
- **Dump**: fatto con le stesse opzioni del sidecar di produzione, `pg_dump -Z1 --no-owner --no-privileges`. File di 1,8 MB.
- **Comando**: `scripts/restore-drill.sh <dump>`.
- **Risultato**: OK. Database nuovo creato e ripristinato senza errori; 23 tabelle e 87.254 righe, tutte uguali alle righe contenute nel dump; nessuna migrazione mancante rispetto al codice.
- **Tempi**: ripristino 20 secondi, prova completa 33 secondi. L'obiettivo era meno di 30 minuti.
- **Prova negativa**: lo stesso dump troncato a 3 MB non compressi. Lo script si ferma al primo errore (`missing data for column "notes"`), esce con codice diverso da zero e cancella il database di prova.

Cosa **non** è stato provato: il download dal bucket con `--from-remote` e la decifratura di rclone. Servono il bucket e le password, che ha solo il proprietario. È la prossima prova da registrare qui, dopo il primo deploy.

## Modello per le prossime prove

- Data, chi, dove (server, versione di PostgreSQL)
- Dump usato e da dove (locale o off-site)
- Comando
- Risultato: tabelle, righe, discrepanze, migrazioni
- Tempi: ripristino e totale
- Note e problemi incontrati
