# Verifica in due passaggi con TOTP

## TL;DR

La verifica in due passaggi chiede, oltre alla password, un codice di sei cifre che cambia ogni 30 secondi e che solo il telefono della persona sa calcolare. L'algoritmo si chiama TOTP e in MusicStudio lo abbiamo scritto con la sola libreria standard di Python, in circa quaranta righe, verificato con i vettori di test ufficiali della RFC 6238. Il segreto di ogni persona è salvato cifrato. Per chi perde il telefono ci sono dieci codici di recupero monouso.

## Il problema reale

Una password si può rubare, indovinare o riusare da un altro sito. Un insegnante o il titolare di uno studio vede nomi di bambini e incassi: una password sola è poco. Ma la sicurezza non deve diventare un ostacolo per i genitori, che usano l'app ogni tanto dal telefono. Per questo la verifica in due passaggi è disponibile per titolari e insegnanti, non per le famiglie.

Gli SMS sembrano la scelta ovvia, ma costano, richiedono un fornitore e si possono intercettare clonando la SIM. Le app di autenticazione (Google Authenticator, Aegis, 1Password) sono gratuite, funzionano senza rete e si basano su uno standard aperto.

## Come funziona

Immagina un lucchetto con un display. Quando lo hai comprato, il negozio ti ha dato un **segreto condiviso**, e lo hai caricato sul tuo telefono. Da quel momento, sia il lucchetto sia il telefono sanno fare lo stesso calcolo: prendono il segreto e **l'ora**, tagliata a pezzi da 30 secondi, e ne ricavano sei cifre. Se le cifre coincidono, significa che hai il telefono giusto.

I due calcoli non comunicano mai. Per questo funziona anche senza rete. Basta che gli orologi siano più o meno allineati: noi accettiamo il pezzo di tempo precedente e il successivo.

Il calcolo in tre mosse:

1. dividi il tempo Unix per 30: è il "passo";
2. calcola un HMAC-SHA1 del passo con il segreto;
3. dai 20 byte del risultato estrai quattro byte e prendi le ultime sei cifre del numero.

## Come lo abbiamo applicato in MusicStudio

**L'algoritmo.** `backend/apps/accounts/totp.py`:

```python
def code_at(secret: str, step: int, digits: int = DIGITS, algo: str = "sha1") -> str:
    key = base64.b32decode(secret, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", step), algo).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % 10**digits).zfill(digits)
```

Un test (`test_totp.py`) controlla i risultati contro i **vettori ufficiali** della RFC 6238. Se qualcuno tocca l'algoritmo e sbaglia, il test fallisce: è la rete di sicurezza che rende ragionevole non usare una libreria.

**Il codice non si riusa.** Dopo una verifica salviamo il passo in `last_used_step`. Un codice del passo già usato, o precedente, viene rifiutato: chi ha visto il codice sulla spalla di un collega non può riusarlo.

**Il segreto è cifrato.** `MfaDevice.secret` è un `EncryptedTextField`. Chi ha una copia del database non ottiene i segreti.

**Il login a due passi.** Con la verifica attiva, `POST /auth/token/` non restituisce i token. Restituisce `{"mfa_required": true, "mfa_token": ...}`, un valore firmato che dura cinque minuti. Solo `POST /auth/mfa/verify/` con quel valore e un codice valido restituisce la coppia di token. Un codice sbagliato conta come una password sbagliata per il blocco dell'account, quindi non si può indovinare a ripetizione.

**Il recupero.** Alla conferma l'app mostra dieci codici di recupero, una sola volta. Nel database ci sono solo gli SHA-256. Ogni codice si usa una volta. Il codice è casuale con 50 bit di entropia, quindi un hash veloce è sufficiente: uno lento costerebbe tempo senza aggiungere sicurezza.

**Se si perde tutto.** L'operatore usa `python manage.py reset_mfa email`. Il comando scrive nell'audit e il runbook raccomanda di verificare l'identità prima.

## Alternative considerate

- **`pyotp`**: fa la stessa cosa. Abbiamo preferito non aggiungere una dipendenza per quaranta righe con test ufficiali. Resterebbe valida per HOTP o altri algoritmi.
- **SMS**: costo, fornitore esterno, SIM clonabile.
- **Passkey (WebAuthn)**: più sicure, ma richiedono molto lavoro in portale e app. Sono un miglioramento futuro.
- **MFA obbligatoria per tutti**: bloccherebbe i genitori. È una decisione di prodotto.

## Errori comuni e trade-off

- Non salvare l'ultimo passo usato: lo stesso codice funzionerebbe per 90 secondi.
- Accettare finestre troppo larghe: più passi si accettano, più facile è indovinare.
- Salvare il segreto in chiaro: è l'equivalente di salvare una password.
- Dimenticare un percorso di recupero: la persona resta fuori e l'operatore deve intervenire a mano.
- SHA-1 sembra obsoleto, ma dentro un HMAC non ha le debolezze che ha come hash semplice. È anche l'unica scelta che tutte le app leggono.

## Come lo spiegheresti a un colloquio

"Ho implementato il TOTP della RFC 6238 con la libreria standard: un HMAC-SHA1 del tempo diviso 30 secondi, ridotto a sei cifre. L'ho verificato con i vettori ufficiali. Il segreto è cifrato nel database e ricordo l'ultimo passo usato per impedire il riuso del codice. Il login diventa a due passi con un token firmato di cinque minuti, e un codice sbagliato conta per il blocco. Per chi perde il telefono ci sono dieci codici monouso e un comando per l'operatore, che scrive nell'audit."

## Domande di autoverifica

1. **Perché il telefono e il server calcolano lo stesso codice senza parlarsi?**
   Perché condividono il segreto e usano la stessa ora divisa in passi da 30 secondi come ingresso di un HMAC.

2. **A cosa serve `last_used_step`?**
   A impedire che un codice già usato (o precedente) sia accettato di nuovo.

3. **Perché non basta un login che restituisce i token e poi chiede il codice?**
   Perché chi ha la password avrebbe già i token. Per questo la prima risposta contiene solo un token firmato a vita breve.

4. **Perché i codici di recupero usano SHA-256 e non un hash lento?**
   Perché sono casuali con molta entropia: un hash lento non rende più difficile indovinarli e renderebbe lenta la verifica di dieci codici.

5. **Come sappiamo che l'algoritmo è corretto senza una libreria?**
   Perché un test lo confronta con i vettori ufficiali della RFC 6238.
