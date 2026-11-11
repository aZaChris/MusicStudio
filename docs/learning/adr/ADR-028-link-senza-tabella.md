# ADR-028: Link di conferma e di reset senza tabella

- Stato: accettato
- Data: 2026-11-11

## Contesto

Due flussi mandano via email un link a uso singolo: la conferma dell'indirizzo dopo la registrazione e il reset della password. Il link deve scadere, non deve funzionare due volte e non deve rivelare se un indirizzo esiste. Una soluzione classica è una tabella di token da salvare, controllare, segnare come usati e ripulire.

## Decisione

Nessuna tabella. Il link porta due valori, `uid` (l'id utente codificato) e `token`, e solo il backend li sa verificare.

- **Reset password**: usiamo `PasswordResetTokenGenerator` di Django. Il token è un HMAC calcolato anche sull'hash della password e sull'ultimo accesso. Appena la password cambia, il link smette di funzionare. Anche un reset più recente rende inutile quello vecchio, perché ha cambiato la password. Il link vale un'ora (`PASSWORD_RESET_TIMEOUT`).
- **Conferma email**: un valore firmato con `django.core.signing` e un "sale" dedicato, calcolato su (id utente, email, `email_verified`). Vale 48 ore. Una volta confermato l'indirizzo, `email_verified` cambia e il link non torna valido.
- Il portale non interpreta nulla: inoltra `uid` e `token` al backend.
- Le richieste anonime (registrazione, reinvio, reset) rispondono sempre `202` con lo stesso corpo. L'email parte da un task Celery fuori dalla richiesta, così nemmeno il tempo di risposta rivela se l'indirizzo esiste (R3).

## Alternative scartate

- **Tabella di token con hash**: stesse garanzie, ma più codice, da ripulire, e una tabella in più da proteggere.
- **Link basati su JWT**: servirebbe una storia di revoca solo per loro.

## Conseguenze

- Non c'è nulla da ripulire né da far trapelare dal database.
- Il link a uso singolo è una conseguenza di come è calcolato, non di un flag che qualcuno può dimenticare di aggiornare. Un test lo verifica per entrambi i flussi.
- Se cambiasse `SECRET_KEY`, tutti i link in circolazione smetterebbero di funzionare. È accettabile: durano poche ore.
- Gli inviti invece **hanno** una tabella (codice in `apps/accounts/invitations.py`): vanno elencati e revocati, quindi servono uno stato e un token con solo l'hash salvato.
