# ADR-029: Verifica in due passaggi (TOTP) scritta con la libreria standard

- Stato: accettato
- Data: 2026-11-11

## Contesto

Un insegnante o il titolare di uno studio vede dati di bambini e incassi. Una password rubata o indovinata non deve bastare per entrare. La fase 7 aggiunge quindi una seconda verifica per titolari e insegnanti (non per i genitori: restano con la sola password, per non bloccare le famiglie).

Il codice monouso deve funzionare con le app che le persone hanno già (Google Authenticator, Aegis, 1Password). Il proprietario ha escluso gli SMS: costano, richiedono un fornitore e sono più facili da intercettare.

## Decisione

- Usiamo **TOTP, RFC 6238**: sei cifre, passi da 30 secondi, HMAC-SHA1. È la combinazione che tutte le app supportano.
- L'algoritmo sta in un solo file, `apps/accounts/totp.py`, scritto con la **libreria standard** (`hmac`, `hashlib`, `base64`, `secrets`). Sono circa 40 righe.
- Il codice è verificato con i **vettori ufficiali della RFC 6238**. Se un giorno qualcuno tocca l'algoritmo e sbaglia, il test fallisce.
- Si accetta il passo precedente, quello corrente e il successivo, perché l'orologio del telefono non è mai perfetto.
- Si salva `last_used_step`: un codice già usato non vale una seconda volta. Chi ha visto il codice sulla spalla di un collega non può riusarlo.
- Il segreto di ogni persona è salvato **cifrato** (`EncryptedTextField`, ADR-030). Se il database trapela, i segreti non sono leggibili.
- Per chi perde il telefono ci sono **codici di recupero**, monouso, salvati solo come hash.

## Alternative scartate

- **Libreria `pyotp`**: fa la stessa cosa, ma è una dipendenza in più per un algoritmo di 40 righe con test ufficiali. Resta valida se servissero HOTP o altri algoritmi.
- **SMS**: costo, fornitore esterno, intercettazione della SIM.
- **Passkey / WebAuthn**: più sicure, ma molto più lavoro tra portale e app mobile. Sono un miglioramento futuro, non un requisito di oggi.
- **MFA obbligatoria per tutti**: bloccherebbe i genitori. Per ora è opzionale e consigliata a titolari e insegnanti. Renderla obbligatoria è una decisione di prodotto, non tecnica.

## Conseguenze

- Il login diventa in due passi quando la MFA è attiva: la prima risposta non dà token ma un `mfa_token` firmato che dura 5 minuti.
- Se una persona perde telefono e codici di recupero, serve il comando `reset_mfa` da parte dell'operatore del server. Il comando scrive nell'audit.
- SHA-1 qui va bene: dentro un HMAC non ha le debolezze che ha come hash semplice. È anche l'unico valore che tutte le app leggono con certezza.
