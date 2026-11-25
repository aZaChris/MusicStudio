# Un admin di Django blindato

## TL;DR

L'admin di Django è comodo, ma vede i dati di tutti gli studi: è la porta più grande del sistema. In MusicStudio l'abbiamo chiuso in un punto solo. Entrano solo gli operatori, che in produzione devono dare anche il codice TOTP. Valgono gli stessi blocchi dei tentativi dell'API, e si può aggiungere una lista di indirizzi IP ammessi. I record che non devono cambiare sono in sola lettura, le poche modifiche possibili finiscono nel registro, e i campi cifrati non compaiono mai a schermo.

## Il problema reale

Tutta l'API è costruita sull'isolamento: un insegnante vede solo i suoi studenti, un genitore solo i suoi figli. L'admin salta tutto questo per scelta, perché serve all'operatore per l'assistenza: sbloccare un account, chiudere le sessioni, guardare un pagamento. Ma come Django lo installa di default bastava un account `is_staff` per entrare. Si potevano modificare e cancellare i pagamenti, cioè la contabilità dello studio. E nessuno avrebbe saputo chi aveva fatto cosa.

Se a un operatore rubano la password, chi la usa ha in mano tutti gli studi. Se un operatore sbaglia un clic su "elimina selezionati", sparisce un mese di incassi. L'admin era il buco più grande rimasto dopo la fase 7.

## Come funziona, con un'analogia

Pensa alla sala server di un'azienda. Non basta il badge da dipendente: serve un badge speciale, più un codice sul tastierino. La porta non ha un cartello, così chi non deve entrare non sa nemmeno cosa c'è dietro. Dentro, alcuni armadi hanno il vetro: si guardano, non si aprono. Gli armadi che si aprono hanno un registro dove firmi cosa hai preso. E se sbagli il codice troppe volte, il badge si blocca, come quello di tutti gli altri.

Nell'admin il badge speciale è "essere operatore", il tastierino è il TOTP, la porta senza cartello è il 404, gli armadi col vetro sono i modelli in sola lettura e il registro è l'audit.

## Come lo abbiamo applicato in MusicStudio

**Chi è un operatore.** Un utente attivo, `is_staff`, e senza ruolo di studio. Gli account creati con `createsuperuser` hanno il ruolo vuoto. Lo dice una proprietà sul modello:

```python
@property
def is_operator(self) -> bool:
    return self.is_active and self.is_staff and not self.role
```

Un insegnante con `is_staff` forzato non passa: il ruolo di studio vince.

**Un admin site nostro.** `OperatorAdminSite` in `apps/common/admin_site.py`. Per non toccare tutti i `@admin.register` esistenti, una configurazione dell'app admin (`OperatorAdminConfig`, con `default_site`) fa sì che `admin.site` sia il nostro. La configurazione sta in un modulo a parte: con due `AppConfig` nello stesso `apps.py`, Django non sa quale scegliere, e lo abbiamo scoperto al primo avvio.

Il site fa tre cose:
- in `admin_view` risponde **404** a chi è autenticato ma non è operatore, e a chi viene da un indirizzo fuori da `ADMIN_ALLOWED_IPS`;
- in `login` risponde 404 agli indirizzi non ammessi, anche sulla pagina di accesso;
- usa un form di login con un campo in più, il codice.

**Il login.** Il form `OperatorLoginForm` cerca l'utente. Se è bloccato, rifiuta con lo stesso messaggio di una password sbagliata. Poi controlla la password e lo stato di operatore. Se `ADMIN_REQUIRE_TOTP` è attivo, vero per default in produzione, controlla il codice con lo stesso servizio dell'API, `check_second_factor`, che accetta anche i codici di recupero. Ogni errore passa da `register_login_failure`: cinque errori e l'account si blocca, come nell'API. Ogni tentativo scrive `admin.login` nel registro. Il template di login di Django mostra solo email e password, quindi ne abbiamo uno che aggiunge il campo del codice.

**Le due regole dei modelli**, in `apps/common/admin_mixins.py`:

- `ReadOnlyAdmin` nega aggiunta, modifica e cancellazione, e toglie le azioni in blocco. Lo usano i record definitivi (pagamenti, ricevute, contestazioni, consensi, registro) e i dati che cambiano solo dai service (lezioni, pacchetti, studenti): una modifica dall'admin salterebbe i controlli su sovrapposizioni e saldo.
- `AuditedAdmin` registra ogni salvataggio con i **nomi** dei campi cambiati, mai i valori: un'email nel registro sarebbe una copia di dati personali. Lo usa solo l'utente.

**I test che fanno da guardia.** `test_admin_inventory.py` elenca tutto ciò che è registrato. Fallisce se un modello non ha una regola, se un modello in sola lettura si può scrivere, o se una schermata mostra un campo cifrato. Al primo giro ha trovato una sorpresa: la libreria dei JWT registra da sola le sue tabelle dei token, che contengono i refresh token interi. Ora sono fuori dall'admin.

## Alternative considerate

`django-otp` o `django-two-factor-auth`: una seconda implementazione del TOTP accanto alla nostra, già testata, più template da mantenere. Proteggere l'admin solo con una VPN o con il proxy: utile come strato in più, ma non è sotto il nostro controllo. Togliere del tutto l'admin: l'operatore perderebbe la vista per l'assistenza. Usare il `LogEntry` di Django come registro: il superuser lo può modificare, quindi non prova niente.

## Errori comuni e trade-off

- **403 invece di 404.** Un 403 conferma che l'admin esiste e che quell'utente esiste. Il 404 non dice niente.
- **Messaggi diversi per "bloccato" e "password sbagliata".** Aiutano chi attacca a capire quali account esistono. Il messaggio deve essere lo stesso.
- **Rendere tutto modificabile "per comodità".** L'admin salva direttamente il modello e salta `services.py`. Un pacchetto modificato a mano può avere un saldo impossibile.
- **Scrivere i valori nell'audit.** Il registro diventerebbe una seconda copia dei dati personali, da esportare e cancellare.
- **Il rischio al deploy.** Con il TOTP obbligatorio, un operatore che non l'ha ancora attivato resta fuori. Non si può attivarlo prima del deploy, perché è questa fase a rendere gli operatori idonei: si spegne l'obbligo per il primo deploy, si attiva il TOTP e poi si riaccende. È scritto nell'ADR-041.

## Come lo spiegheresti a un colloquio

L'admin di Django è l'unico posto che salta l'isolamento tra clienti, quindi l'ho trattato come la porta più importante. Entra solo un operatore, cioè un account staff senza ruolo di cliente, e in produzione con il TOTP che già usavamo nell'API. Gli errori contano per lo stesso blocco dell'accesso API, e a chi non deve entrare rispondo 404. I record contabili e i dati gestiti dai service sono in sola lettura, e l'unico modello modificabile registra chi ha cambiato quali campi, senza i valori. Un test elenca tutto ciò che è registrato nell'admin, e così ha trovato i token JWT esposti da una libreria.

## Domande di autoverifica

1. **Perché un insegnante con `is_staff` non entra nell'admin?**
   Perché operatore vuol dire anche "senza ruolo di studio": il ruolo di studio vince sul flag. Un flag messo per sbaglio non apre l'accesso ai dati di tutti.
2. **Perché le lezioni sono in sola lettura, anche se non sono record "definitivi"?**
   Perché si modificano solo da `services.py`, che controlla sovrapposizioni e saldo del pacchetto. L'admin salverebbe il modello saltando quei controlli.
3. **Cosa scrive l'audit quando l'operatore cambia l'email di un utente?**
   `admin.change` con chi, quale utente, e il nome del campo `email`. Non scrive il valore nuovo né quello vecchio.
4. **Come rientra un operatore che ha perso il telefono e i codici di recupero?**
   Con il comando `reset_mfa` dal terminale del server, che scrive `mfa.reset_by_operator` nel registro. Non esiste una schermata web per farlo.
5. **Cosa ha trovato il test d'inventario dell'admin al primo giro?**
   Le tabelle dei token di simplejwt, registrate in automatico dalla libreria, che contengono i refresh token interi. Sono state tolte dall'admin.
