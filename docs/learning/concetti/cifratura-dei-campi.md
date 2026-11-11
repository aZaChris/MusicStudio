# Cifratura dei campi nel database

## TL;DR

Le note che un insegnante scrive su un allievo possono contenere informazioni delicate. In MusicStudio sono cifrate prima di entrare nel database, con Fernet della libreria `cryptography`. Le chiavi sono una lista: la prima cifra, tutte decifrano, così si può ruotare una chiave senza fermare niente. Il prezzo è che un campo cifrato non si può cercare né ordinare con SQL. In produzione l'app non parte senza una chiave valida.

## Il problema reale

Un database ha molti modi di finire fuori controllo: un backup copiato, un dump mandato a una persona sbagliata, un account del provider compromesso. Se le note delle lezioni sono in chiaro, chi ha il file le legge tutte. Sono testo libero su bambini: salute, difficoltà di apprendimento, situazioni in famiglia.

La cifratura del disco del server protegge dal furto del server fisico, ma non da un backup o da un dump che esce dall'infrastruttura, perché il disco, una volta montato, mostra tutto in chiaro. La cifratura **applicativa** protegge anche da questo: nel database c'è solo testo illeggibile, e la chiave sta altrove.

## Come funziona

Pensa a una cassetta di sicurezza in banca. Il contenuto è nella cassetta, ma la chiave ce l'hai tu. Se qualcuno porta via la cassetta, non può aprirla.

**Fernet** è una cassetta già pronta e ben fatta. Combina AES-128 (che mescola i dati) con un HMAC-SHA256 (che garantisce che nessuno li abbia toccati). Se un singolo byte cambia, la decifratura **fallisce**, invece di restituire spazzatura. Ogni cifratura include un'ora e un valore casuale, quindi lo stesso testo cifrato due volte dà due risultati diversi.

**MultiFernet** è un portachiavi: cifra con la prima chiave e prova tutte le altre per decifrare. È quello che rende possibile la **rotazione**: aggiungi la chiave nuova in testa, tutto continua a funzionare, poi ricifri tutto con la nuova e butti la vecchia.

## Come lo abbiamo applicato in MusicStudio

**Il campo.** `backend/apps/common/fields.py` definisce `EncryptedTextField`. Per il codice è un normale campo di testo: cifra quando salva e decifra quando legge.

```python
class Lesson(models.Model):
    # Free text about a (often minor) student: encrypted at rest (ADR-030).
    notes = EncryptedTextField(blank=True)
```

Si usa nello stesso modo di prima, e un test controlla con una query SQL grezza che nel database ci sia un valore che inizia con `gAAAA`, l'intestazione di un token Fernet.

**Le chiavi.** La variabile `FIELD_ENCRYPTION_KEYS` è una lista separata da virgole. In `backend/config/settings/prod.py` non ha valore predefinito: senza chiavi valide l'app non parte. Un errore di battitura emerge al deploy, non alla prima nota letta.

**La rotazione.**

1. Metti la chiave nuova **prima** della vecchia: `NUOVA,VECCHIA`. Deploy.
2. Lancia `python manage.py rotate_field_keys`. Ricifra tutti i campi cifrati in blocchi da 500 righe, con SQL diretto, senza toccare `updated_at`.
3. Togli la chiave vecchia. Deploy.

Il comando si può ripetere senza danni.

**La migrazione dei dati esistenti.** Le note già presenti erano in chiaro. Una migrazione di schema ha cambiato il tipo di campo, una **seconda** migrazione, di dati, ha cifrato le righe. Le due sono separate perché PostgreSQL rifiuta un `ALTER TABLE` se ci sono controlli di chiave esterna in sospeso nella stessa transazione.

**Cosa si cifra.** Le note delle lezioni e il segreto TOTP. Non cifriamo i nomi: servono per cercare e ordinare, e li proteggono l'isolamento tra studi e l'anonimizzazione.

## Alternative considerate

- **`pgcrypto` dentro PostgreSQL**: la chiave viaggia in ogni query e finisce nei log del database.
- **`django-fernet-fields`**: non più mantenuta.
- **Cifrare tutto**: non si potrebbe più cercare un allievo per nome.
- **Solo cifratura del disco**: utile ma non copre i backup che escono dal server.

## Errori comuni e trade-off

- **Perdere la chiave** significa perdere i dati. Le chiavi vanno conservate fuori dal repository e fuori dal solo server.
- **Cifrare un campo su cui si fanno ricerche**: non funziona. Un campo cifrato non si filtra, non si ordina e non ha un indice utile.
- **Tenere la chiave nel codice**: l'unica chiave nel codice è quella pubblica di sviluppo. Il secret scanning la conosce e la ignora, perché è pubblica per scelta.
- **Dimenticare la rotazione**: una chiave mai ruotata che trapela espone tutto lo storico. Per questo c'è il comando e la procedura nel runbook.
- Il costo di cifrare è trascurabile a questa scala.

## Come lo spiegheresti a un colloquio

"Le note sui minori sono cifrate a livello di applicazione con Fernet, quindi anche un backup rubato non le mostra. Ho scritto un campo Django che cifra al salvataggio e decifra alla lettura. Le chiavi sono una lista con MultiFernet: la prima cifra, tutte decifrano, e un comando ricifra tutto durante la rotazione. In produzione l'app non parte senza una chiave valida. Il limite è che un campo cifrato non si può cercare, quindi lo uso solo per testo che si legge intero."

## Domande di autoverifica

1. **Perché la cifratura del disco non basta?**
   Perché il disco montato mostra tutto in chiaro. Un backup o un dump che esce dal server non è protetto.

2. **Perché `FIELD_ENCRYPTION_KEYS` è una lista?**
   Per ruotare le chiavi: la prima cifra, tutte decifrano, e si può passare alla chiave nuova senza fermare il servizio.

3. **Cosa succede se un byte di un valore cifrato viene alterato?**
   La decifratura fallisce, perché Fernet è autenticato. Non si ottiene testo sbagliato in silenzio.

4. **Perché i nomi degli allievi non sono cifrati?**
   Perché servono per cercare e ordinare. Li proteggono altri meccanismi: isolamento tra studi, anonimizzazione, audit.

5. **Perché lo schema e i dati hanno due migrazioni separate?**
   Perché PostgreSQL rifiuta un `ALTER TABLE` con controlli di chiave esterna in sospeso nella stessa transazione.
