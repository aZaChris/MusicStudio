# ADR-018: Revoca dei token (logout vero)

- Stato: accettato
- Data: 2026-11-09

## Contesto

Fino alla fase 3 il "logout" esisteva solo sul dispositivo: l'app dimenticava i token, ma il server li accettava ancora. Il refresh token durava 14 giorni. Chi ne rubava una copia poteva rinnovare la sessione per due settimane, anche dopo il logout della vittima. Era il punto aperto di OWASP API2 (Broken Authentication).

Un JWT è autosufficiente: il server lo verifica con la firma, senza guardare il database. È il suo vantaggio, ed è anche il motivo per cui non si può "spegnere" un token già emesso senza tenere una lista.

## Decisione

- Usiamo l'app `token_blacklist` inclusa in simplejwt. Ogni refresh token emesso viene registrato (`OutstandingToken`); un token revocato finisce in `BlacklistedToken`.
- `BLACKLIST_AFTER_ROTATION = True`: quando un refresh token viene usato per rinnovare, quello vecchio muore. Se qualcuno ne riusa una copia, riceve 401.
- Nuovo endpoint `POST /api/v1/auth/logout/` con il refresh token del dispositivo. Il token deve appartenere all'utente autenticato. Un token di un altro utente riceve lo stesso 400 di un token malformato, così l'endpoint non rivela niente. Un secondo logout dello stesso token non fa niente e risponde 205.
- "Revoca tutte le sessioni" di un account: comando `manage.py revoke_sessions <email>` e azione nell'admin. Nessun endpoint pubblico.
- Un task giornaliero cancella i token scaduti, così le tabelle non crescono all'infinito.
- **I token di accesso non sono controllati contro la lista.** Per limitare il danno, la loro durata predefinita scende da 60 a 15 minuti.

## Alternative scartate

- **Lista nera anche per i token di accesso**: una lettura sul database (o su Redis) a ogni richiesta. È esattamente il costo che il JWT evita.
- **Sessioni lato server**: abbandonare il JWT e cambiare il contratto per i client esistenti.
- **Un numero di versione sull'utente** (da incrementare per invalidare tutto): anche questo richiede una query per richiesta, e non permette il logout di un solo dispositivo.

## Conseguenze

- Dopo un logout, il token di accesso funziona ancora per al massimo 15 minuti. È un compromesso dichiarato.
- Il client deve rinnovare il token di accesso più spesso. Con la rotazione lo fa già.
- Login e rinnovo fanno una scrittura in più (la riga di `OutstandingToken`). Le richieste normali non cambiano.
- Cambiare `JWT_SIGNING_KEY` resta il "pulsante rosso": invalida tutti i token di tutti gli utenti.
