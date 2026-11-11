# PostgreSQL 16 e 18: cosa abbiamo verificato e cosa no

Data: 11 novembre 2026. Scritto per decidere con chi amministra il server **senza correre rischi**.
Ogni affermazione dice da dove viene: "provato" (l'ho eseguito io), "documentato" (note ufficiali di
PostgreSQL o di Docker, lette per questo documento) o "da verificare" (nessuna prova ancora).

## Decisione di oggi

- **Produzione e staging restano su PostgreSQL 16**, con l'immagine fissata alla versione provata:
  `postgres:16.15-alpine` (prima era `16-alpine`, che cambia da sola a ogni minore).
- **La CI esegue tutta la suite su 16.15 e su 18.6** (matrice nel job `backend`). Se un giorno si passa
  alla 18 sarà una cosa già misurata, non un salto al buio.
- **Non si passa alla 18 sul server finché non c'è un motivo** e finché non si fa il giro descritto
  più sotto. PostgreSQL 16 riceve correzioni fino al **9 novembre 2028**, la 18 fino al
  **14 novembre 2030** (documentato: pagina "Versioning policy" di postgresql.org). Non c'è fretta.

## Versioni minori (16.x e 18.x)

Le versioni minori correggono errori e falle di sicurezza e **non cambiano il formato dei dati**:
si aggiornano sostituendo i programmi e riavviando, senza dump e ripristino (documentato).

- Ultima 16: **16.15**. Ultima 18: **18.6** (documentato: pagina delle release).
- Fissare il tag (`16.15-alpine`) dà un comportamento prevedibile, ma ha un costo: **gli aggiornamenti di
  sicurezza non arrivano da soli**. Regola: ogni due o tre mesi, o quando esce una correzione di sicurezza,
  si leggono le note della minore nuova, si alza il tag nel Compose **e** nella matrice della CI, si lancia
  la CI, si fa il deploy su staging prima che sul resto.

## Cosa è stato provato

- **Provato su 18.6**: l'intera suite del backend, **740 test verdi**, con copertura 95-96%. Compresi i
  vincoli di esclusione sulle lezioni (estensione `btree_gist`), le note cifrate, gli inviti e la
  cancellazione.
- **Provato su 18.6**: il giro di backup e ripristino. Un database migrato e popolato è stato scaricato con le
  stesse opzioni del backup di produzione (`pg_dump -Z1 --no-owner --no-privileges`) e ripristinato con
  `scripts/restore-drill.sh`: 30 tabelle, 198 righe, **0 differenze**, nessuna migrazione in sospeso, i due
  vincoli `lesson_no_student_overlap` e `lesson_no_teacher_overlap` presenti.
- **Provato su 16.15, ma solo fino alla fase 6**: le fasi 1-6 (la suite di allora, il restore drill e la prova di
  carico, come scritto nei loro documenti) girarono su PostgreSQL 16 (16.15).
- **NON provato su 16**: **i test della fase 7** non sono mai stati eseguiti su PostgreSQL 16. Su questo
  computer non c'è un PostgreSQL 16 con le estensioni `contrib`, quindi ho usato il 18. La prova su 16 la
  darà la CI al primo push (job `backend (postgres 16.15)`). **Finché quel job non è verde, la fase 7 non va
  messa su un server con PostgreSQL 16.**

## Cosa cambia dalla 16 alla 18 (documentato) e cosa significa per MusicStudio

Fonte: note di rilascio della 18, sezione "Migration to Version 18".

- **Serve dump e ripristino, `pg_upgrade` o replica logica.** I file di dati di una 16 non si aprono con una
  18. Per noi: si fa con `pg_dump` e ripristino, come nel restore drill. I dump fatti dalla 16 si ripristinano
  nella 18; **il contrario non è garantito**, quindi prima di passare si tiene un dump della 16.
- **`initdb` attiva i checksum dei dati di default.** Per noi: nessun problema con dump e ripristino
  (il nuovo cluster nasce con i checksum). Se si usasse `pg_upgrade`, le impostazioni devono coincidere.
- **Le abbreviazioni dei fusi orari hanno un'altra priorità.** Per noi: nessun impatto, usiamo nomi IANA
  (`Europe/Rome`) e calcoliamo le durate in UTC (vedi i problemi noti in `CLAUDE.md`).
- **L'autenticazione MD5 è deprecata** (avvisi in `CREATE ROLE`). Per noi: l'immagine Docker crea gli utenti con
  SCRAM. Da verificare sul server di Elio: `SHOW password_encryption;` deve dire `scram-sha-256`.
- **`VACUUM` e `ANALYZE` processano anche le tabelle figlie nelle ereditarietà.** Non usiamo ereditarietà.
- **`COPY FROM` non tratta più `\.` come fine file nei CSV.** Non usiamo CSV. I dump in formato testo
  (`COPY ... FROM stdin`) restano validi: è il formato che abbiamo ripristinato con successo sulla 18.
- **Tabelle partizionate unlogged vietate, trigger AFTER con un altro ruolo, privilegi delle regole,
  colonne di `pg_backend_memory_contexts`.** Non li usiamo. Lo script `scripts/measure-resources.sh` interroga
  solo la dimensione del database e il numero di lezioni.
- **La ricerca full-text legge i file con il provider di collation del cluster.** Non usiamo la ricerca
  full-text né `pg_trgm`.
- **Le chiavi esterne richiedono collation deterministiche.** Usiamo quelle di default.

Altri cambiamenti documentati che possono modificare il **comportamento** senza essere incompatibilità:

- **Il planner cambia** (join con se stesso eliminati, riordino di `DISTINCT`, `IN (VALUES ...)`). Può cambiare
  l'**ordine** dei risultati di una query senza `ORDER BY`. I modelli hanno un ordinamento esplicito e la suite
  è verde, ma "tutte le liste hanno un ordine esplicito" **non l'ho verificato una per una**: da verificare
  prima di un passaggio.
- **I/O asincrono e `effective_io_concurrency` a 16.** Più parallelismo in lettura. Su un server piccolo
  condiviso con altri servizi, **da misurare** (RAM e CPU) con `scripts/measure-resources.sh`.
- **Monitoraggio**: alcune colonne di `pg_stat_wal` e `pg_stat_io` spariscono. Solo se Elio ha cruscotti che le
  leggono.

Django 5.2 dichiara di supportare "PostgreSQL 14 e superiori" (documentato) e usiamo psycopg 3.3.5. Le note di
rilascio che ho letto non citano esplicitamente la 18: l'evidenza che abbiamo è la nostra suite verde.

## Docker: cosa cambia con l'immagine 18 (documentato)

- Con l'immagine 18 la cartella dei dati cambia: `PGDATA` diventa `/var/lib/postgresql/18/docker` e il volume
  va montato su **`/var/lib/postgresql`**, non più su `/var/lib/postgresql/data`.
- Oggi il Compose monta `db-data:/var/lib/postgresql/data`. **Cambiare solo il tag a `18-alpine` non basta e può
  far partire un database vuoto**: il testo ufficiale avverte che un montaggio sul vecchio percorso "non
  mantiene i dati" quando il container viene ricreato. Cosa succeda esattamente con un volume esistente la
  documentazione **non lo dice**, quindi non lo si prova su dati veri.
- Il Compose attuale **non viene modificato** per la 18: va cambiato insieme (tag, percorso del volume) in una
  prova su un volume nuovo.

## Se un giorno si passa alla 18: percorso a rischio zero

1. Tenere il dump più recente della 16 (e una prova di ripristino riuscita su di esso).
2. Controllare che la CI sia verde su 16.15 e 18.6.
3. Su una **macchina di prova**, non sul server di Elio: Compose con l'immagine 18, volume **nuovo** montato su
   `/var/lib/postgresql`, ripristino del dump della 16, `scripts/restore-drill.sh` e
   `manage.py migrate --check`, poi i controlli di `docs/operations/runbook.md`.
4. Misurare RAM e tempi con `scripts/measure-resources.sh` e il load test.
5. Solo se tutto torna: finestra di manutenzione, dump finale, nuovo volume, ripristino, controlli. **Il
   volume della 16 resta intatto** per tornare indietro.

## Cosa chiedere a Elio

- Quale versione di PostgreSQL ha già sul server, se condivide l'istanza con altri servizi (il nostro Compose ha
  il suo `db`) e quanta RAM libera ha.
- `SHOW password_encryption;` e `SHOW data_checksums;` sul database che userà, se non usa il nostro container.
- Se i suoi backup coprono il volume `db-data` con un `pg_dump` o uno snapshot atomico (ADR-026).
