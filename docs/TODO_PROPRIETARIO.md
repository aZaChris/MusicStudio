# Cosa devi fare tu (senza il deploy)

Stato al 11 novembre 2026, fine della fase 7. Il **deploy di staging** ha la sua guida: `docs/DEPLOY_STAGING.md`
(DNS, Coolify, variabili, verifiche, primo account). Il webhook Stripe e la protezione dei branch restano in
`docs/CHECKLIST_17.md`.
Qui ci sono le azioni che richiedono te e che puoi fare **adesso**, in ordine. I segreti non vanno mai
nel repository né in chat.

Branch in gioco: `main` (backend e portale, nel worktree `~/MusicStudio-web`) e
`mobile` (app, nel worktree `~/MusicStudio-mobile`). Dal 12 novembre 2026 `main` è il branch di produzione,
protetto da un ruleset: ci si arriva solo con la CI verde.

## 1. Rileggi e pubblica i branch

1. In `~/MusicStudio-web`: `git log --oneline origin/main..HEAD` per vedere cosa parte.
2. `git push origin main`.
3. In `~/MusicStudio-mobile`: `git push origin mobile`.
4. Su GitHub, scheda **Actions**, aspetta i risultati. Ti aspetta questo:
   - `backend (postgres 16.15)` e `backend (postgres 18.6)`: **devono essere verdi tutti e due**. Il primo è
     la prima volta in assoluto che i test della fase 7 girano su PostgreSQL 16.
   - `secrets`: **prima esecuzione di gitleaks sulla cronologia**. Se segnala qualcosa, **non ignorarlo**:
     scrivimi il nome della regola e il file (non il valore). Un falso positivo si mette in `.gitleaks.toml`;
     un segreto vero va **cambiato**, non solo nascosto.
   - `frontend`, `web-image` e la CI mobile.
5. Se qualcosa è rosso, incolla l'errore e lo sistemo.

## 2. Chiave di cifratura (obbligatoria) — FATTO, resta l'incolla al deploy

L'app **non parte in produzione** senza `FIELD_ENCRYPTION_KEYS`: cifra le note sugli allievi e i segreti
della verifica in due passaggi. **Se la perdi, perdi le note.**

1. La chiave è stata generata e salvata nel gestore di password (fatto). Se serve rigenerarla:
   `cd ~/MusicStudio-web/backend && uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
2. Alla fase di deploy: incollala nella variabile `FIELD_ENCRYPTION_KEYS` di Coolify.
3. Per ruotarla in futuro: `docs/learning/concetti/cifratura-dei-campi.md`, sezione "La rotazione".

## 3. Controllo dell'APK e dell'app — FATTO

1. Apri https://expo.dev/accounts/azachris/projects/musicstudio-app?tab=activity e guarda lo stato
   dell'ultima build. Se è fallita, incolla qui le ultime righe del log.
2. L'APK che hai già scaricato è **precedente** alle novità: non ha secondo passo, invito, privacy. Per
   provarle serve una build nuova dal branch `mobile` aggiornato:
   `cd ~/MusicStudio-mobile && npx eas-cli login` (una volta) e `npx eas-cli build --platform android --profile preview`.
3. L'APK `preview` è già puntato all'API di staging (`https://stagingapimusic.christianseminerio.dev/api/v1`):
   funzionerà **solo dopo il deploy**. Prima del deploy, per provarla davvero, avvia il backend in locale
   e usa `EXPO_PUBLIC_API_BASE_URL=http://<IP-del-tuo-PC>:8000/api/v1` con `npx expo start`.

## 4. Decisioni da prendere con Elio — LASCIATO STARE per ora

Le domande sono in `docs/operations/postgresql-16-vs-18.md`, sezione "Cosa chiedere a Elio". In breve:

1. Che versione di PostgreSQL ha, se l'istanza è condivisa, quanta RAM libera ha.
2. Che i suoi backup coprano il database di MusicStudio con un `pg_dump` o uno snapshot atomico, conservato
   fuori dal server e cifrato, **con una prova di ripristino registrata** (ADR-026, `docs/operations/restore-drill.md`).
3. Chi riceve gli avvisi se i backup falliscono.

Da decidere tra voi: **restare su PostgreSQL 16** (è la scelta del repository, fissata a `16.15`).
Non passare alla 18 sul suo server senza il giro del documento.

## 5. Testi legali (bozze) da far validare

Tre file in `docs/privacy/`: `registro-trattamenti.md`, `informativa-famiglie.md`,
`informativa-insegnanti.md`. Sono **bozze scritte da me guardando il codice**, non un parere legale.

1. Completa i punti **DA COMPLETARE** (cerca con `grep -n "DA COMPLETARE" docs/privacy/*.md`): ragione
   sociale dello studio titolare, contatto privacy, fornitori reali (hosting, SMTP, Sentry).
2. Fai validare i tre file da un consulente privacy o un avvocato **prima** di usare MusicStudio con
   famiglie vere. Chiedi in particolare di confermare i tempi: allievi archiviati anonimizzati dopo 24 mesi,
   pagamenti conservati 10 anni, registro delle azioni 12 mesi, registrazioni non confermate 7 giorni.
3. Se cambiano, i valori sono in `backend/apps/privacy/services.py` (costanti in cima alla sezione
   "Retention") e nell'ADR-032. Dimmelo e li aggiorno insieme ai testi.
4. Quando i testi sono approvati, cambia il valore di `PRIVACY_NOTICE_VERSION` (oggi `2026-11-draft`):
   i nuovi consensi registreranno la versione giusta.

## 6. Email vere e Sentry (dopo il deploy, ma prepara adesso)

Preparare adesso fa risparmiare il giorno del deploy: `docs/CHECKLIST_17.md`, passo 2 (account SMTP,
dominio mittente, record DNS SPF/DKIM). La prova che conferma, reset e inviti **arrivano davvero** (task
T058) si fa dopo il deploy: registrati dal portale, controlla anche la cartella spam, apri il link.

**Indirizzi di prova**: servono solo per ricevere i messaggi. Su Proton puoi usare un indirizzo per ruolo
(account diversi) oppure alias con il più (`tuonome+titolare@proton.me`, controlla che il tuo piano li
supporti). L'app tratta ogni indirizzo come una persona diversa.

**Controllo dell'SMTP** prima dei giri completi, dal terminale del `backend` in Coolify:

```
python manage.py shell -c "from django.core.mail import send_mail; send_mail('prova', 'funziona', None, ['tuonome+prova@proton.me'])"
```

Deve stampare `1` e l'email arriva dopo pochi secondi (guarda anche lo spam). Se dà errore, incollalo
senza la password.

**Sentry** (facoltativo): il codice è già pronto, **non** incollare lo snippet `sentry_sdk.init` che
mostra la pagina di Sentry (sovrascriverebbe la nostra configurazione, che toglie email e token prima
dell'invio). Crea il progetto con piattaforma **Django**, metti il DSN in `SENTRY_DSN` su Coolify (mai nel
repository) con `SENTRY_ENVIRONMENT=staging`, poi `python manage.py raise_test_error`: l'errore deve
comparire in Sentry. Non attivare i log né le metriche di Sentry: non passano dalla nostra ripulitura.
Controlla nelle impostazioni dell'organizzazione che la regione dei dati sia quella europea.

## 7. Vault Obsidian

Sul computer dove c'è il vault, aggiungi a `20 Progetti/MusicStudio/Decisioni MusicStudio.md` le righe
della fase 7 (tabella Scelta | Perché | Scartato). Le righe pronte sono nella risposta in cui ti ho
parlato del vault; se non le hai più, chiedimele e le rigenero dall'indice (`docs/learning/00-indice.md`,
"Riepilogo della fase 7") e dagli ADR 027-032.

## 8. NotebookLM

Già esportato in `C:\Users\Christian\Documents\doc_music_studio` (cartella "Fase 7 - Sicurezza privacy e
account"). Dopo ogni modifica ai documenti rilancia `bash scripts/export-study-docs.sh` e ricarica in
NotebookLM i file segnati UPDATED.

## Quando hai fatto

Scrivimi quali passi sono andati e, per quelli che no, il messaggio d'errore esatto. Io chiudo i task T048,
T055, T056, T057 e T058 nel file `specs/007-security-privacy-accounts/tasks.md`.
