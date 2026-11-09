# Revoca dei token JWT: logout vero, rotazione e lista nera

## TL;DR

Un JWT è un "biglietto firmato": il server lo verifica con la firma, senza guardare il database. È veloce, ma un biglietto già emesso non si può ritirare. In MusicStudio abbiamo reso revocabili i refresh token con la lista nera di simplejwt: il logout spegne il token del dispositivo, la rotazione spegne ogni token già usato e un operatore può chiudere tutte le sessioni di un account. I token di accesso restano non revocabili, ma durano solo 15 minuti.

## Il problema reale

Fino alla fase 3 il logout esisteva solo sul telefono. L'app cancellava i token dalla memoria, ma il server continuava ad accettarli. Il refresh token durava 14 giorni.

Immagina un genitore che perde il telefono, o un insegnante che usa il computer della scuola e se ne va. Chi trova il dispositivo, o chi ha copiato il token da un log o da una rete insicura, può rinnovare la sessione per due settimane. Anche se l'utente ha fatto "logout". Era il punto aperto della voce API2 della OWASP Top 10, Broken Authentication.

## Come funziona

Pensa al braccialetto di un festival. All'ingresso ti danno un braccialetto con un sigillo che non si può falsificare. Agli altri cancelli nessuno chiama la biglietteria: guardano il sigillo e ti fanno passare. Questo è il token di accesso. È veloce proprio perché nessuno deve controllare un elenco.

Il braccialetto però scade presto. Per averne uno nuovo vai a uno sportello con la tua ricevuta: il refresh token. Lo sportello ti dà un braccialetto nuovo e una ricevuta nuova, e strappa quella vecchia. Questa è la **rotazione**.

Ora la **revoca**. Lo sportello tiene un registro delle ricevute strappate: la **lista nera**. Se qualcuno si presenta con una ricevuta già strappata, o con una ricevuta di chi ha detto "ho perso tutto", viene respinto. Il registro si consulta solo allo sportello, non a ogni cancello. Per questo il braccialetto già al polso resta valido fino a quando scade.

Questo è il compromesso di fondo. Puoi revocare in modo immediato solo quello che controlli a ogni richiesta. E controllare a ogni richiesta costa una lettura sul database.

## Come lo abbiamo applicato in MusicStudio

**La lista nera.** Abbiamo attivato l'app `rest_framework_simplejwt.token_blacklist`, già inclusa in simplejwt. Ogni refresh token emesso viene registrato nella tabella `OutstandingToken`. Un token revocato ha una riga in `BlacklistedToken`.

**La configurazione** in `backend/config/settings/base.py`:

```python
"ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=15)),
"REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=14)),
"ROTATE_REFRESH_TOKENS": True,
"BLACKLIST_AFTER_ROTATION": True,
```

Prima il token di accesso durava 60 minuti e il refresh usato restava valido. Ora il refresh usato muore subito, e il token di accesso dura un quarto.

**Il logout.** Nuovo endpoint `POST /api/v1/auth/logout/`, con il refresh token del dispositivo nel corpo. La logica sta nel service `logout()` in `backend/apps/accounts/services.py`. Controlla la firma e la scadenza, controlla che sia un refresh token, controlla che appartenga all'utente autenticato e poi lo mette nella lista nera. Due dettagli contano:

- un token di un altro utente riceve lo stesso errore di un token malformato, così l'endpoint non rivela se il token di qualcun altro è valido;
- un secondo logout dello stesso token risponde comunque 205, senza errore. Ripetere un logout non deve fare danni.

**Revocare tutto.** Il service `revoke_all_sessions(user)` mette nella lista nera tutti i refresh token non scaduti di un account. Lo usano il comando `manage.py revoke_sessions <email>` e un'azione dell'admin. Non c'è un endpoint pubblico: è un'operazione da operatore.

**La pulizia.** Ogni login e ogni rinnovo aggiungono una riga. Un task Celery giornaliero cancella i token scaduti, quindi le tabelle restano piccole.

**I test**, in `backend/apps/accounts/tests/test_logout.py`, provano tutti i casi: logout e poi rinnovo rifiutato, logout ripetuto, token di un altro utente, token di accesso al posto del refresh, riuso di un refresh già ruotato, revoca di tutte le sessioni che non tocca gli altri utenti, pulizia solo dei token scaduti.

## Alternative considerate

**Lista nera anche per i token di accesso.** Revoca immediata, ma una query a ogni richiesta. È esattamente il costo che il JWT voleva evitare.

**Sessioni lato server.** Il server tiene tutte le sessioni e le può chiudere quando vuole. È il modello classico di Django. Ma cambia il contratto per i client che già usano i JWT.

**Un numero di versione sull'utente.** Il token contiene la versione, e per invalidare tutto si incrementa il numero. Richiede comunque una lettura a ogni richiesta, e non permette di chiudere un solo dispositivo.

**Cambiare la chiave di firma.** Invalida tutti i token di tutti gli utenti. È il "pulsante rosso" per una chiave esposta, non uno strumento quotidiano.

## Errori comuni e trade-off

- **Credere che un logout lato client basti.** Il server non sa niente di quello che il client cancella.
- **Rotazione senza lista nera.** Il refresh token cambia a ogni rinnovo, ma quello vecchio resta valido. La rotazione da sola non protegge.
- **Rivelare informazioni nel logout.** Rispondere "questo token non è tuo" invece di "token non valido" conferma che il token esiste.
- **Dimenticare la pulizia.** La tabella dei token cresce a ogni login e rinnovo, per sempre.
- **Trade-off dichiarato:** dopo il logout, il token di accesso già emesso funziona ancora per al massimo 15 minuti. Lo accettiamo per non aggiungere una query a ogni richiesta.

## Come lo spiegheresti a un colloquio

Un JWT si verifica con la firma, senza database, quindi un token emesso non si può ritirare. Per avere un logout vero ho attivato la lista nera di simplejwt sui refresh token, con la rotazione: ogni refresh usato muore, e il logout mette nella lista quello del dispositivo. Non controllo i token di accesso contro la lista, perché costerebbe una query a ogni richiesta; in cambio durano 15 minuti. Il logout controlla che il token appartenga all'utente e risponde allo stesso modo per un token altrui o malformato, così non fa da oracolo. C'è anche un comando per chiudere tutte le sessioni di un account, e un task giornaliero che pulisce i token scaduti.

## Domande di autoverifica

1. **Perché un JWT non si può revocare "da solo"?**
   Perché il server lo verifica solo con la firma e la scadenza, senza consultare un elenco. Finché la firma è valida e il token non è scaduto, viene accettato.

2. **Cosa fa la rotazione, e perché serve la lista nera insieme?**
   A ogni rinnovo dà un refresh token nuovo. Con la lista nera, quello vecchio diventa inutilizzabile: chi ne ha copiato uno lo scopre al primo tentativo.

3. **Perché i token di accesso non sono nella lista nera?**
   Perché controllarli richiederebbe una lettura a ogni richiesta. Si limita il rischio con una durata breve, 15 minuti.

4. **Perché il logout di un token altrui risponde 400 come un token malformato?**
   Per non rivelare se il token di un altro utente è valido. Un errore diverso farebbe da oracolo.

5. **Cosa succede se cambi `JWT_SIGNING_KEY`?**
   Tutti i token, di tutti gli utenti, diventano invalidi. Tutti devono rifare il login. Si usa solo se la chiave è stata esposta.
