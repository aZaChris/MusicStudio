# KB: Dopo il deploy della fase 10 l'admin rifiutava ogni accesso

## Sintomo
Il 26 novembre 2026, dopo il deploy della fase 10 in produzione con `ADMIN_REQUIRE_TOTP=false`, il login dell'admin rispondeva sempre con il messaggio generico "inserisci email e password corrette". Password giusta, account non bloccato (sbloccato comunque con `unlock_account`), variabile presente in Coolify e deploy rifatto dopo averla aggiunta. Poco prima l'admin sembrava funzionare.

## Causa radice
In produzione **non esisteva nessun account operatore**. L'account con cui il proprietario entra nel portale e su Swagger è un account normale, non staff: non è mai stato un account dell'admin. Dalla fase 10 l'admin accetta solo `User.is_operator`, cioè attivo, `is_staff` e senza ruolo di studio (ADR-041). Ogni altro account riceve lo stesso messaggio generico di una password sbagliata, apposta, per non rivelare quali account esistono.

L'impressione che "prima funzionasse" veniva da una verifica che aveva solo aperto la pagina di login, quella con il campo "One-time code", oppure aveva usato una sessione ancora aperta. Non c'era stato un login completo.

Il messaggio generico ha nascosto la causa: password sbagliata, account bloccato e "non sei un operatore" sono indistinguibili da fuori, e lo sono per scelta.

## Come l'abbiamo confermata
Prima abbiamo escluso le altre cause. La variabile era presente e il deploy era stato rifatto. L'account era stato sbloccato. E con `ADMIN_REQUIRE_TOTP=false` il form ignora il codice, quindi non poteva essere un codice sbagliato.

Poi abbiamo elencato gli account staff dal Terminal del container `backend` (comando nel runbook, con le email mascherate). Il risultato era **nessuna riga**. La riga `28 objects imported automatically` che compare in output è solo un avviso di `manage.py shell` e all'inizio ha confuso la lettura.

Un primo tentativo di leggere l'account per email era fallito con `DoesNotExist`, perché nel comando era rimasto il segnaposto dell'email: per questo il comando dell'elenco non chiede nessun indirizzo.

## Risoluzione
- Creato un operatore separato con `python manage.py createsuperuser`, usando un alias dell'email del proprietario (`...+ops@gmail.com`). L'elenco ora mostra una riga con `ruolo: ''`, `staff: True`, `superuser: True`.
- Confermata la sua email con `confirm-email/resend/`: gli account di `createsuperuser` nascono non confermati, e l'API ne rifiuta il login.
- Attivato il suo TOTP da Swagger (`mfa/setup`, `mfa/confirm`), con i codici di recupero salvati nel password manager.
- Tolta `ADMIN_REQUIRE_TOTP` e rideployato. La prova finale ha dato rifiuto senza codice e accesso con il codice.
- Il TOTP attivato per sbaglio sull'account normale è rimasto: ora protegge anche l'accesso al portale.

## Lezione per il futuro
Quando un accesso viene rifiutato con un messaggio generico voluto, la prima cosa da verificare è che l'account abbia **davvero** i requisiti, leggendo il database, prima di cercare problemi di password, blocchi o variabili. "La pagina si apre" non vuol dire "posso entrare": una verifica dopo il deploy deve fare il login completo.

Un'altra trappola della stessa giornata: il dominio dell'API, che ospita anche admin e Swagger, è diverso da quello del portale, e il portale risponde a ogni indirizzo che non conosce con la sua pagina bianca. Un controllo di salute fatto sul dominio sbagliato "non mostra nulla".

E infine: uno screenshot di Swagger include il comando `curl` con la password e il corpo della risposta con i token. Prima di condividerlo vanno coperti. Se succede, si cambia la password dall'API (`password/change/`), che chiude anche tutte le sessioni aperte.

## Riferimenti
- `docs/operations/runbook.md`, sezione "Admin solo per operatori (fase 10)"
- `docs/learning/adr/ADR-041-admin-solo-operatori-con-totp.md`
- `backend/apps/common/admin_site.py` (`OperatorLoginForm`), `backend/apps/accounts/models.py` (`User.is_operator`)
