# ADR-030: Cifratura applicativa dei campi sensibili

- Stato: accettato
- Data: 2026-11-11

## Contesto

Le note delle lezioni sono testo libero su bambini e ragazzi: possono contenere salute, difficoltà di apprendimento, situazioni familiari. Una copia del database (un backup rubato, uno dump finito nel posto sbagliato) non deve mostrarle in chiaro. Anche il segreto del secondo fattore (ADR-029) non deve essere leggibile da chi ha il database.

## Decisione

- Un campo `EncryptedTextField` in `apps/common/fields.py` cifra quando salva e decifra quando legge. Per il codice Python il testo resta un normale testo.
- Cifratura **Fernet** (AES-128-CBC più HMAC-SHA256, quindi autenticata) dalla libreria `cryptography`, tramite `MultiFernet`.
- Le chiavi stanno in `FIELD_ENCRYPTION_KEYS`: una lista, la prima cifra, tutte decifrano. Questo permette la **rotazione**: si aggiunge una chiave nuova in testa, si fa il deploy, si lancia `manage.py rotate_field_keys` che ricifra tutto, poi si toglie la chiave vecchia.
- In produzione l'app **non parte** senza una chiave valida. In sviluppo e nei test c'è una chiave fissa e pubblica.
- Si cifrano `Lesson.notes` e il segreto TOTP. Una stringa vuota resta vuota.
- Le righe esistenti sono cifrate da una migrazione dati separata dalla migrazione di schema: PostgreSQL rifiuta un `ALTER TABLE` con controlli di chiave esterna ancora in sospeso nella stessa transazione.

## Alternative scartate

- **`pgcrypto` nel database**: la chiave viaggerebbe in ogni query e finirebbe nei log di PostgreSQL.
- **`django-fernet-fields`**: non più mantenuta.
- **Solo cifratura del disco**: protegge dal furto del server, non da un backup o da un dump che esce dall'infrastruttura.

## Conseguenze

- Un testo cifrato non si può cercare, filtrare o ordinare in SQL. Le note non si filtrano mai, quindi non si perde nulla. Un campo da cercare non va cifrato così.
- Perdere tutte le chiavi significa perdere le note. Le chiavi vanno conservate (non nel repository) e nel runbook c'è la procedura di rotazione.
- Costo: una cifratura per ogni nota letta o scritta, trascurabile a questa scala.
