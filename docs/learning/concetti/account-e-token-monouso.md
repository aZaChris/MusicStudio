# Account, link a uso singolo e blocco dell'account

## TL;DR

Un account sicuro non è solo una password hashata. Servono link di conferma e di reset che funzionano una volta sola, risposte che non rivelano se un'email esiste, e un blocco contro chi prova password a ripetizione. In MusicStudio i link non usano nessuna tabella: sono firmati e si invalidano da soli. Gli inviti invece hanno una tabella, ma salviamo solo l'hash del token. Dopo cinque password sbagliate l'account si blocca per un tempo che raddoppia.

## Il problema reale

Fino alla fase 6 gli account li creava solo l'operatore da riga di comando. Per accogliere persone vere servono tre cose nuove: registrarsi da soli, recuperare una password dimenticata, invitare altre persone nello studio. Ognuna apre una porta, e ogni porta ha i suoi errori classici.

Il primo: la schermata "password dimenticata" che dice "questa email non esiste". Sembra gentile. Ma permette a chiunque di scoprire chi usa il servizio. In un'app con dati di bambini, sapere che "l'email di Maria è registrata nello studio di musica" è già un'informazione.

Il secondo: il link di reset che resta valido per giorni, o che si può usare dieci volte. Se l'email viene letta da un'altra persona, o il link finisce in un log, chiunque può cambiare la password.

Il terzo: la password indovinata. Un limite di richieste per indirizzo IP non basta, perché chi attacca può cambiare indirizzo ogni volta.

## Come funziona

Immagina la portineria di un palazzo.

Se chiedi "vive qui la signora Rossi?", il portiere educato risponde sempre allo stesso modo: "Se vive qui, le faccio avere il messaggio". Non conferma e non smentisce. Questo è l'**anti-enumerazione**: stessa risposta, stesso tempo.

Il biglietto per ritirare le chiavi di riserva ha un timbro con l'ora e la data di emissione, e un codice che il portiere sa ricalcolare. Una volta ritirate le chiavi, il portiere cambia la serratura: il biglietto vecchio non apre più niente. Il biglietto non ha bisogno di un registro, perché il suo valore dipende da qualcosa che cambia quando lo si usa. Questo è il **link a uso singolo senza tabella**.

Per gli ospiti invitati, invece, il portiere tiene un quaderno: nome dell'ospite, chi l'ha invitato, fino a quando vale. Non scrive però la parola d'ordine, solo un'impronta di essa. Se qualcuno ruba il quaderno, non può entrare. Questo è l'**invito con hash**.

Infine, se qualcuno sbaglia la parola d'ordine cinque volte di fila, il portiere dice "ripassa fra un quarto d'ora". Alla volta dopo, "fra mezz'ora". Questo è il **blocco progressivo**.

## Come lo abbiamo applicato in MusicStudio

**Link di reset.** In `backend/apps/accounts/tokens.py` usiamo il generatore di Django. Il token è un HMAC calcolato anche sull'hash della password: cambiata la password, il link muore.

```python
def make_reset_token(user: User) -> str:
    return default_token_generator.make_token(user)
```

**Link di conferma.** È un valore firmato su (id, email, `email_verified`), valido 48 ore. Appena l'indirizzo è confermato il contenuto non coincide più e il link smette di funzionare:

```python
def make_confirm_token(user: User) -> str:
    return signing.dumps([user.pk, user.email, user.email_verified], salt=_CONFIRM_SALT)
```

**Risposta uniforme.** Registrazione, reinvio e reset rispondono sempre `202` con lo stesso corpo. L'email vera parte da un task Celery dopo la richiesta, così nemmeno il tempo di risposta cambia. Se qualcuno registra un indirizzo già usato, il proprietario riceve una email "qualcuno ha provato a registrarsi".

**Inviti.** `Invitation` ha un token da 32 byte casuali. Nel database c'è solo lo SHA-256. Il token in chiaro esiste una volta sola: nell'email. All'accettazione si controlla che chi ha invitato sia ancora attivo e abbia ancora in carico gli allievi: se l'insegnante nel frattempo ha perso un allievo, l'invito non porta più al suo dato.

**Blocco.** In `backend/apps/accounts/services.py`, dopo cinque password sbagliate l'account si blocca per `15 minuti × 2^livello`, con un massimo di 24 ore. Un login riuscito azzera il livello. Un contatore atomico con `F()` conta bene anche i tentativi paralleli:

```python
User.objects.filter(pk=user.pk).update(failed_logins=F("failed_logins") + 1)
fresh = User.objects.select_for_update().get(pk=user.pk)
if fresh.failed_logins >= LOCK_AFTER_FAILURES:
    duration = min(BASE_LOCK * 2**fresh.lock_level, MAX_LOCK)
```

Password sbagliata, email sconosciuta e account bloccato danno la stessa risposta `401`. Chi sbaglia non impara nulla.

## Alternative considerate

- **Tabella di token con hash** anche per conferma e reset: stesse garanzie, più codice da scrivere e ripulire.
- **`django-axes`** per il blocco: è una dipendenza pensata per le sessioni e l'admin. Per un login JWT bastano tre campi sull'utente.
- **CAPTCHA**: un servizio di terzi. Fuori portata per ora.

## Errori comuni e trade-off

- Rispondere in modo uguale ma inviare l'email dentro la richiesta: la risposta è identica, ma il tempo no, e il tempo tradisce.
- Dimenticare che il blocco si può usare contro la vittima: chi conosce l'email di qualcuno può bloccargli l'account. Il limite di 24 ore e il reset via email lo contengono. È un compromesso scelto, e documentato.
- Rifiutare un account non confermato con un messaggio diverso **prima** di controllare la password: rivelerebbe che l'email esiste. Noi lo diciamo solo dopo una password corretta.
- Se cambia `SECRET_KEY`, tutti i link in circolazione smettono di funzionare. Accettabile, durano ore.

## Come lo spiegheresti a un colloquio

"Per gli account ho evitato di rivelare se un'email esiste: stessa risposta e stesso tempo, con l'email spedita da un task. I link di reset e conferma sono firmati e dipendono da qualcosa che cambia quando li usi, quindi sono a uso singolo senza una tabella. Gli inviti hanno una tabella perché si elencano e si revocano, ma salvo solo l'hash del token. Contro le password indovinate ho un blocco progressivo per account, oltre al limite per IP. Il rischio che qualcuno blocchi un'altra persona l'ho accettato e limitato con un tetto di 24 ore e il reset."

## Domande di autoverifica

1. **Perché il link di reset non ha bisogno di una tabella?**
   Perché il token dipende dall'hash della password. Quando la password cambia, il token calcolato non coincide più e il link muore.

2. **Perché l'email di reset parte da un task e non dalla richiesta?**
   Perché il tempo di risposta non deve dipendere dall'esistenza dell'account. Se la richiesta aspettasse l'invio, risponderebbe più lenta per gli indirizzi veri.

3. **Perché negli inviti salviamo solo l'hash del token?**
   Perché se il database trapela, gli hash non permettono di costruire un link valido.

4. **Cosa succede alla quinta password sbagliata e perché i tentativi paralleli sono contati bene?**
   L'account si blocca 15 minuti, poi 30, e così via. Il contatore usa `F()` e un lock di riga, quindi due richieste insieme non si sovrascrivono.

5. **Qual è il rischio del blocco per account e come lo limitiamo?**
   Qualcuno può bloccare un'altra persona. Lo limitiamo con un massimo di 24 ore, il reset via email che toglie il blocco e il comando `unlock_account` per l'operatore.
