# Registro dei trattamenti (art. 30 GDPR)

> **BOZZA — da validare** da un professionista (consulente privacy o avvocato) prima di usare MusicStudio con famiglie vere.
> Versione dell'informativa collegata: `2026-11-draft` (impostazione `PRIVACY_NOTICE_VERSION`).

Questo registro descrive che dati tratta MusicStudio, perché, per quanto tempo e con chi li condivide. È scritto guardando il codice, non un modello generico: ogni riga corrisponde a qualcosa che l'applicazione fa davvero.

## Chi è chi

- **Titolare del trattamento**: lo studio musicale (o l'insegnante) che usa MusicStudio con i suoi allievi. [DA COMPLETARE: ragione sociale, indirizzo, contatto privacy dello studio]
- **Responsabile del trattamento**: chi gestisce MusicStudio per lo studio. [DA COMPLETARE: da chiarire con un professionista se il gestore del servizio sia responsabile o contitolare]
- **Interessati**: genitori, allievi (in gran parte minorenni), insegnanti e titolari degli studi.

## Trattamenti

### 1. Account e accesso
- **Dati**: nome, cognome, email, lingua, password (salvata solo come hash PBKDF2), data di accettazione dei termini; per chi attiva la verifica in due passaggi, un segreto cifrato e codici di recupero (solo hash).
- **Finalità**: permettere l'accesso e proteggerlo (blocco dopo password sbagliate, reset via email).
- **Base giuridica**: esecuzione del servizio richiesto.
- **Conservazione**: finché l'account esiste. Le registrazioni mai confermate si cancellano dopo 7 giorni.

### 2. Allievi e lezioni
- **Dati**: nome, cognome, strumento, indicazione "maggiorenne sì/no" (nessuna data di nascita), lezioni (data, ora, stato) e note dell'insegnante (testo libero, **cifrato** nel database).
- **Finalità**: organizzare e ricordare le lezioni.
- **Base giuridica**: esecuzione del servizio; per i minori, il **consenso del genitore**, registrato con data e versione dell'informativa.
- **Conservazione**: finché l'allievo è attivo. Un allievo archiviato è anonimizzato dopo 24 mesi dall'ultima attività.

### 3. Pacchetti di lezioni e pagamenti
- **Dati**: pacchetto (numero lezioni, prezzo, date), pagamento (importo, data, metodo, stato). Nessun dato di carta: i pagamenti online passano da Stripe.
- **Finalità**: gestione contabile dello studio.
- **Base giuridica**: obbligo legale e contratto.
- **Conservazione**: 10 anni. [DA VALIDARE: periodo di conservazione contabile]. Alla cancellazione di un account, importi e date restano senza nomi.

### 4. Promemoria e comunicazioni
- **Dati**: email del genitore, data e ora della lezione.
- **Finalità**: promemoria delle lezioni, email dell'account (conferma, reset, inviti).
- **Conservazione**: l'invio è registrato finché esiste l'account.

### 5. Registro delle azioni (audit)
- **Dati**: chi ha fatto cosa e quando (accessi, cambi di password, inviti, consensi, esportazioni, cancellazioni, pagamenti registrati). Solo identificativi, mai nomi o email nel dettaglio.
- **Finalità**: sicurezza e responsabilità; il titolare dello studio vede le voci del proprio studio.
- **Conservazione**: 12 mesi.

### 6. Log tecnici ed errori
- **Dati**: richieste (percorso, esito, durata, id utente). Per scelta di progetto nessun nome, email, password, codice o token.
- **Finalità**: sicurezza e correzione degli errori. Sentry, se attivo, riceve gli errori con i dati personali rimossi.
- **Conservazione**: secondo la configurazione del server. [DA COMPLETARE]

## Destinatari e fornitori

- **Hosting**: il server dell'operatore. [DA COMPLETARE: fornitore e Paese]
- **Stripe**: pagamenti online (oggi in modalità di prova).
- **Fornitore SMTP**: invio delle email. [DA COMPLETARE]
- **Sentry**: segnalazione errori, opzionale. Riceve gli errori con nomi, email, token e cookie già rimossi dall'applicazione; i log e le metriche di Sentry restano disattivati. [DA COMPLETARE: confermare la regione dei dati (UE) nelle impostazioni dell'organizzazione e i tempi di conservazione di Sentry]

## Misure di sicurezza

Cifratura delle note e dei segreti nel database, isolamento tra studi verificato da test automatici, blocco dell'account e verifica in due passaggi, registro delle azioni, scansione dei segreti nel repository, collegamenti HTTPS con HSTS.

## Diritti degli interessati

Un genitore o uno studente adulto può **scaricare** i propri dati e **cancellare** il proprio account dall'applicazione, e **ritirare** il consenso. La cancellazione anonimizza, non elimina i pagamenti (vedi trattamento 3).
