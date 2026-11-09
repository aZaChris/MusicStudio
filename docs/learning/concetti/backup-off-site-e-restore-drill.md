# Backup off-site e prova di ripristino

## TL;DR

Un backup serve solo se sopravvive al disastro e se si riesce a ripristinarlo. In MusicStudio i dump giornalieri del database ora vengono copiati, cifrati, su un bucket fuori dal server. Uno script ripristina un dump in un database nuovo e controlla che ogni tabella abbia le righe attese. La prova è stata eseguita su 78.000 lezioni: 87.254 righe identiche, 20 secondi di ripristino.

## Il problema reale

Dalla fase 1 un container faceva un `pg_dump` ogni giorno e teneva 7 copie giornaliere, 4 settimanali e 6 mensili. Sembrava a posto. Ma i dump stavano in un volume dello **stesso server** del database.

Pensa a cosa può andare storto. Il disco del server si rompe. Il provider chiude l'account. Qualcuno cancella il progetto in Coolify. Un attaccante entra nel server e cancella tutto. In tutti questi casi i dati e i backup spariscono insieme.

E c'era un secondo problema, più sottile: nessuno aveva mai provato a ripristinare un dump. Un backup mai ripristinato è una speranza, non una garanzia. Magari il file è troncato, o mancano dei permessi, o lo schema non corrisponde al codice. Lo scopri solo il giorno in cui ti serve.

## Come funziona

Pensa ai documenti importanti di casa. Tenere le fotocopie nello stesso cassetto degli originali non serve a niente se la casa brucia. Le metti in una cassetta di sicurezza in banca: è il **backup off-site**. E le chiudi in una busta sigillata, così l'impiegato della banca non le legge: è la **cifratura lato client**.

Ma una volta all'anno conviene aprire la cassetta e controllare che le fotocopie siano leggibili e complete. Questa è la **prova di ripristino** (restore drill).

Due numeri descrivono un piano di backup. L'**RPO** (recovery point objective) è quanti dati puoi perdere al massimo: con un backup al giorno, fino a 24 ore. L'**RTO** (recovery time objective) è quanto tempo serve per tornare operativi.

## Come lo abbiamo applicato in MusicStudio

**La copia off-site.** Nel file `docker-compose.coolify.yml` c'è un nuovo servizio, `offsite`, con l'immagine ufficiale di rclone. rclone si configura tutto con variabili d'ambiente. Ci sono due "remote": `bucket` è lo storage S3-compatibile (Backblaze B2, Cloudflare R2 o Hetzner, mai AWS); `offsite` è un remote `crypt` sopra il primo, che cifra contenuto e nomi dei file prima di inviarli. Il provider vede solo dati cifrati.

**`copy`, non `sync`.** Questa scelta l'abbiamo cambiata durante l'implementazione. Il piano diceva `rclone sync`, che rende il bucket identico al volume locale. Ma pensaci: se il volume locale viene svuotato, per errore o da un attaccante, alla copia successiva `sync` svuota anche il bucket. Il backup off-site sparirebbe proprio nello scenario per cui esiste. Con `copy` non si cancella mai niente in remoto. Le copie vecchie si eliminano per età:

```sh
rclone copy /backups offsite: --exclude "last/**" \
  && rclone delete offsite: --min-age "${OFFSITE_KEEP_DAYS}d"
```

Il limite è 190 giorni, poco più della conservazione mensile.

**Gli allarmi.** Se la copia fallisce, il container chiama un URL opzionale, per esempio un controllo di healthchecks.io, che manda un'email. Se l'ultima copia riuscita ha più di 26 ore, l'healthcheck del container diventa "unhealthy" e Coolify lo mostra.

**Dump portabili.** Il sidecar ora usa `pg_dump --no-owner --no-privileges`. Senza queste opzioni il dump contiene istruzioni come "il proprietario di questa tabella è l'utente X", che falliscono su un server dove X non esiste.

**Lo script di prova.** `scripts/restore-drill.sh` prende un dump locale, oppure lo scarica dal bucket con `--from-remote`. Poi crea un database nuovo, ripristina fermandosi al primo errore, e confronta le righe di ogni tabella. Il trucco: in un dump in formato testo, i dati di ogni tabella sono un blocco `COPY` con una riga per record. Contare le righe dei blocchi dà le righe attese. Il dump è la fotografia, quindi non serve un file di conteggi separato. Infine lo script controlla che lo schema corrisponda alle migrazioni del codice e stampa i tempi.

**La prova eseguita.** Un database creato con `seed_loadtest` (78.000 lezioni) è stato esportato con le stesse opzioni del sidecar: 1,8 MB. Risultato: 23 tabelle, 87.254 righe, zero differenze, nessuna migrazione mancante. Ripristino in 20 secondi, prova completa in 33. Poi la prova negativa: lo stesso dump troncato. Lo script si è fermato con `missing data for column "notes"`, è uscito con errore e ha cancellato il database di prova. Tutto è registrato in `docs/operations/restore-drill.md`.

## Alternative considerate

**I backup S3 integrati di Coolify.** Funzionano solo per i database creati come risorse separate di Coolify, non per un servizio dentro un Compose.

**`rclone sync`.** Spiegato sopra: mette a rischio proprio le copie off-site.

**Regole di ciclo di vita del bucket.** Ogni provider le configura a modo suo, e stanno fuori dal repository.

**pgBackRest o l'archiviazione continua dei WAL.** Permettono di tornare a un istante preciso, perdendo pochi secondi di dati. Per uno studio di musica, un giorno di dati come perdita massima è accettabile, e la complessità in più non lo è.

## Errori comuni e trade-off

- **Backup sullo stesso server dei dati.** Protegge dagli errori umani, non dalla perdita del server.
- **Non provare mai il ripristino.** È l'errore più comune e il più costoso.
- **Perdere le chiavi di cifratura.** Senza le password di rclone, i backup off-site sono rumore. Vanno salvate anche fuori dal server.
- **Ripristinare sopra il database di produzione.** Si ripristina sempre in un database nuovo, si controlla, e solo dopo si sposta l'applicazione.
- **Trade-off:** con un backup al giorno l'RPO è 24 ore. Va bene per questo prodotto, non per una banca.

## Come lo spiegheresti a un colloquio

I dump giornalieri del database restavano sullo stesso server, quindi perdendo il server avremmo perso anche i backup. Ho aggiunto un sidecar con rclone che li copia ogni giorno su un bucket S3-compatibile, cifrati lato client con il remote crypt. Uso `copy` e non `sync`, perché con `sync` un volume locale svuotato svuoterebbe anche il bucket; le copie vecchie le elimino per età. Poi ho scritto uno script di ripristino che lavora su un database nuovo e confronta le righe di ogni tabella con quelle contenute nel dump. L'ho eseguito su 78.000 lezioni: 20 secondi, zero differenze, e un dump troncato viene rifiutato.

## Domande di autoverifica

1. **Perché un backup sullo stesso server non basta?**
   Perché un guasto del server, la chiusura dell'account o un attacco eliminano insieme i dati e i backup.

2. **Perché `rclone copy` e non `rclone sync`?**
   Perché `sync` replica anche le cancellazioni: un volume locale svuotato svuoterebbe il bucket alla copia successiva.

3. **Da dove prende lo script le righe attese per ogni tabella?**
   Dal dump stesso: ogni tabella è un blocco `COPY` con una riga per record. Il dump è la fotografia del momento del backup.

4. **Cosa sono RPO e RTO, e quanto valgono qui?**
   L'RPO è quanti dati si possono perdere: fino a 24 ore. L'RTO è il tempo per tornare operativi: il ripristino misurato è di 20 secondi, a cui si aggiungono download e riavvio.

5. **Perché il dump usa `--no-owner --no-privileges`?**
   Per poterlo ripristinare con qualunque utente PostgreSQL, anche su un server dove l'utente originale non esiste.
