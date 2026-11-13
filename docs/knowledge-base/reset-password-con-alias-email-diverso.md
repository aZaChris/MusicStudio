# La password dimenticata «non arriva»: l'indirizzo scritto non era quello registrato

## Sintomo

Su staging, la pagina «Password dimenticata» mostrava il messaggio di conferma («se l'indirizzo è
registrato, ti abbiamo mandato un link»), ma nella casella non arrivava nessuna email. Il
backend rispondeva 202 e il `worker` non aveva nessun task `send_account_email` di tipo
`password_reset`.

## Causa radice

L'account era stato registrato con un indirizzo con alias, del tipo `nome+titolare@gmail.com`.
Gmail consegna anche `nome@gmail.com` nella stessa casella, ma per MusicStudio sono due indirizzi
diversi. Scrivendo l'indirizzo senza l'alias, l'app non trovava nessun account. La risposta a
«password dimenticata» è la stessa in ogni caso, apposta, per non rivelare chi ha un account
(nessuna enumerazione), quindi dalla pagina non si capiva che non era partito niente.

## Come l'abbiamo confermata

- Il log del `worker` non conteneva nessun task `password_reset` dopo l'invio del modulo.
- Un'email «qualcuno ha provato a registrarsi con la tua email», arrivata prima, riportava come
  destinatario l'indirizzo con l'alias: era quello registrato.
- Riprovando con l'indirizzo esatto, l'email di reset è arrivata.

## Risoluzione

Nessuna modifica al codice: il comportamento è voluto. Si usa l'indirizzo esatto con cui ci si è
registrati. La guida di staging, nella sezione sul primo account, ricorda già che ogni alias con
il `+` è una persona diversa per l'app.

## Lezione per il futuro

Una risposta uguale in ogni caso protegge gli account, ma nasconde anche gli errori di digitazione.
Quando una funzione «non fa niente» in silenzio, la prova è nei log del processo che avrebbe dovuto
reagire (qui il `worker`), non nel messaggio a schermo. Nei test manuali con più ruoli conviene
scrivere l'alias nel nome dell'account, per riconoscerlo.

## Riferimenti

- `backend/apps/accounts/services.py` (`request_password_reset`)
- `docs/learning/concetti/account-e-token-monouso.md`
