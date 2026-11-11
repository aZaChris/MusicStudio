# Audit log: chi ha fatto cosa

## TL;DR

Un audit log è un registro che non si riscrive: dice chi ha fatto un'azione delicata, su cosa, quando e con quale esito. In MusicStudio una tabella `AuditEntry` è scritta in modo esplicito dai service (accessi, cambio password, MFA, inviti, consensi, esportazioni, cancellazioni, pagamenti). Le voci non si modificano e non si cancellano una per una. Il titolare dello studio legge quelle del proprio studio. Un test fallisce se un'azione non ha un controllo.

## Il problema reale

Quando succede qualcosa di strano ("chi ha cambiato quel pagamento?", "qualcuno ha provato a entrare nel mio account?") i log tecnici non bastano. Sono pensati per chi gestisce il server, sparsi su più file, e per scelta non contengono dati personali. Serve un posto dove sia scritto, in modo stabile e leggibile da una persona non tecnica, che cosa è successo.

Un registro del genere ha però un rischio: se si può modificare, non prova niente. E se contiene troppi dati personali, diventa un secondo archivio da proteggere e da ripulire.

## Come funziona

È il registro firme di un ufficio. Si scrive sempre in fondo, con la penna, e non si strappano pagine. Ogni riga dice: chi, cosa, su che pratica, quando, come è andata. Il direttore può leggere le righe del proprio ufficio, non quelle degli altri uffici.

Due scelte decidono se il registro è utile:

- **Chi scrive**. Se scrive automaticamente "qualsiasi cosa cambi", si riempie di rumore e copia dati. Se scrivono i punti dove avviene l'azione, ogni riga ha un significato.
- **Cosa scrive**. Solo identificativi e fatti semplici, mai nomi, email o password.

## Come lo abbiamo applicato in MusicStudio

**Una funzione sola.** `record()` in `backend/apps/audit/services.py`:

```python
audit.record(
    audit.Action.PAYMENT_RECORD,
    actor=actor,
    target=payment,
    studio_id=payment.student.studio_id,
    metadata={"method": payment.method, "amount": str(payment.amount)},
)
```

La chiamano i **service**, nel punto in cui l'azione avviene. Non usiamo i segnali di Django: scatterebbero anche per le modifiche dall'admin e per le fixture dei test, e non conoscerebbero l'autore.

**Cosa entra nei metadati.** Solo numeri, testo e booleani; ogni altro valore viene scartato in silenzio. Il bersaglio è un tipo e un id. Il test `test_audit.py` verifica che un dizionario annidato o un `None` non passino.

**Non si riscrive.** Il modello rifiuta `save()` su una voce esistente e `delete()` su una singola voce, con un errore. L'unico percorso che cancella è il task di conservazione, in blocco, per le voci più vecchie di 12 mesi. Anche l'admin è in sola lettura.

**L'id della richiesta.** Ogni voce porta l'id della richiesta HTTP, lo stesso che compare nei log JSON. Da una voce si risale alle righe tecniche dello stesso momento.

**Chi può leggere.** `GET /api/v1/audit/`, solo per il titolare, con filtri per azione e per data e paginazione. Il filtro vive nel selettore in `backend/apps/audit/selectors.py`: le voci con lo studio del titolare, più gli accessi dei suoi insegnanti. Gli accessi non hanno uno studio, perché una persona potrebbe appartenerne a più d'uno, e il titolare non vede mai gli accessi dei genitori.

**Una per ogni azione.** In `backend/apps/audit/tests/test_coverage.py` ogni valore dell'elenco `Action` deve avere un controllo, oppure comparire nell'elenco delle azioni controllate altrove. Se qualcuno aggiunge un'azione e dimentica il controllo, il test fallisce. Non può però accorgersi di un service delicato nuovo che non registra nulla: quello resta una responsabilità della revisione.

## Alternative considerate

- **`django-auditlog` o `simple-history`**: registrano ogni cambio di campo e copiano dati personali altrove. Il contrario della minimizzazione.
- **Trigger nel database**: non conoscono l'utente né la richiesta.
- **Solo i log tecnici**: non sono leggibili dal titolare e non hanno una struttura stabile.

## Errori comuni e trade-off

- Metterci tutto "per sicurezza": ogni campo personale in più è un obbligo di conservazione e di cancellazione.
- Dimenticare il tempo di conservazione: un audit senza scadenza è un archivio di dati personali senza base giuridica.
- Scrivere nell'audit **dentro** una transazione che poi fallisce: la voce sparisce con il rollback. Per gli accessi falliti questo conta, perché la richiesta finisce con un errore 401. Nel nostro caso la scrittura avviene fuori dalle transazioni che vengono annullate.
- Considerare l'audit una prova a prova di manomissione: chi ha accesso al database può comunque alterarlo. Rende difficile l'errore e l'abuso ordinario, non un amministratore ostile.

## Come lo spiegheresti a un colloquio

"Ho aggiunto un registro delle azioni delicate: una tabella append-only scritta in modo esplicito dai service, con autore, bersaglio, studio, esito e l'id della richiesta. I metadati accettano solo valori semplici, così non ci finiscono dati personali. Il titolare vede le voci del proprio studio, filtrate per azione e data. Le voci si cancellano solo con la conservazione a 12 mesi. Un test fallisce se un'azione dell'elenco non ha un controllo."

## Domande di autoverifica

1. **Perché i service chiamano `record()` invece di usare i segnali?**
   I segnali scattano anche per l'admin e le fixture, e non conoscono l'autore. La chiamata esplicita si legge, si cerca e si testa.

2. **Come garantiamo che una voce non si riscriva?**
   `save()` su una voce esistente e `delete()` singolo lanciano un errore; solo il task di conservazione cancella, in blocco.

3. **Perché i metadati scartano i valori annidati e i `None`?**
   Per impedire che nomi, email o dizionari interi finiscano nel registro: restano solo fatti semplici.

4. **Perché un titolare non vede gli accessi dei genitori?**
   Perché gli accessi non hanno uno studio e un genitore può essere in più studi. Il titolare vede solo quelli dei propri insegnanti.

5. **Cosa non riesce a scoprire il test di copertura?**
   Un service delicato nuovo che non registra niente. Il test conosce solo le azioni già nell'elenco.
