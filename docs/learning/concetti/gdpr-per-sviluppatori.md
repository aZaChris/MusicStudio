# GDPR per sviluppatori: consenso, esportazione, cancellazione

## TL;DR

Il GDPR dà alle persone dei diritti sui propri dati: sapere cosa abbiamo, averne una copia, farli cancellare. Per uno sviluppatore significa progettare quattro cose: raccogliere meno dati possibile, registrare il consenso dei genitori per i minori, offrire un'esportazione e offrire una cancellazione. In MusicStudio la cancellazione **anonimizza sul posto** invece di eliminare a cascata, perché lo studio deve conservare i pagamenti. Un task notturno applica i tempi di conservazione.

## Il problema reale

MusicStudio contiene dati di bambini: nome, strumento, come va a lezione. Chi accede a quei dati sono genitori e insegnanti. Se un genitore ci chiede "cancellate tutto", rispondere "scrivi all'amministratore" non basta. E se cancelliamo davvero tutto con un `DELETE` a cascata, distruggiamo anche lo storico dei pagamenti, e il totale incassato dallo studio cambia a posteriori. La contabilità deve restare.

C'è poi un tema più sottile: i dati che non raccogliamo non dobbiamo proteggerli. Per questo non chiediamo data di nascita, indirizzo o telefono.

*Nota: questo documento è tecnico, non è un parere legale. I testi per le famiglie sono bozze da far validare a un professionista.*

## Come funziona

Pensa a una biblioteca che ha le schede dei lettori.

- **Minimizzazione**: la scheda contiene solo ciò che serve. Non l'indirizzo di casa, se non lo usiamo.
- **Consenso**: per i bambini, la firma di un genitore sulla scheda, con la data e la versione del regolamento firmato.
- **Accesso e portabilità**: chiunque può chiedere una fotocopia completa della propria scheda.
- **Cancellazione**: la persona può chiedere di togliere il proprio nome. Ma i registri dei prestiti, che servono alla contabilità, restano: si cancella il nome, non la riga.
- **Conservazione**: dopo un certo tempo le schede inattive si anonimizzano da sole.

## Come lo abbiamo applicato in MusicStudio

**Consenso.** `ConsentRecord` in `backend/apps/privacy/models.py`: chi l'ha dato, per quali figli, per quale versione dell'informativa (`PRIVACY_NOTICE_VERSION`), quando, ed eventualmente quando è stato ritirato. Si crea quando un genitore accetta un invito.

**Minorenni.** Un minorenne non ha un account: arriva ai suoi dati il genitore. Solo gli allievi segnati come adulti (`Student.is_adult`, un sì/no scelto dall'insegnante) possono essere invitati. Non salviamo la data di nascita, che cambia valore ogni giorno e non ci serve.

**Esportazione.** `GET /api/v1/privacy/export/` restituisce un file JSON con l'account, i figli, le loro lezioni (le note decifrate), i pacchetti, i pagamenti e i consensi. Cosa contiene lo decide il **ruolo** di chi chiede, non un id nella richiesta: un genitore riceve solo i figli collegati a lui.

```python
def students_of(user: User) -> QuerySet[Student]:
    if user.role == User.Role.STUDENT:
        return Student.objects.filter(user=user)
    return Student.objects.filter(parent_accounts__user=user)
```

**Cancellazione.** `POST /api/v1/privacy/erase/`, con la password. In una transazione, in `backend/apps/privacy/services.py`:

- l'account perde nome ed email (diventa `erased-<uuid>@invalid`), la password diventa inutilizzabile, le sessioni finiscono;
- ogni figlio senza altri genitori diventa "Allievo cancellato #id", con le note svuotate;
- lezioni, pacchetti e pagamenti restano con importi e date, senza nomi;
- se un figlio ha un secondo genitore, il figlio resta e l'insegnante riceve una email;
- con un pagamento online aperto la richiesta è rifiutata (409);
- un titolare può cancellarsi solo con lo studio vuoto.

Un test cerca, colonna per colonna in tutto il database, il nome e l'email della persona cancellata. Se una tabella nuova conservasse un dato personale, il test lo troverebbe.

**Ritirare il consenso.** Ha lo stesso effetto per i figli interessati.

**Conservazione.** `run_retention` gira ogni notte (Celery beat) e si può lanciare a mano: allievi archiviati anonimizzati dopo 24 mesi senza attività, pagamenti eliminati dopo 10 anni, audit dopo 12 mesi, registrazioni mai confermate dopo 7 giorni. Eseguirlo due volte non cambia nulla la seconda.

## Alternative considerate

- **`DELETE` a cascata**: cancella lo storico dei pagamenti e rompe i totali.
- **Soft delete con un flag**: i dati personali restano nel database. Non è cancellazione.
- **Export asincrono via email**: a questa scala, centinaia di righe per famiglia, una risposta sincrona basta.

## Errori comuni e trade-off

- Cancellare l'utente e dimenticare le copie: inviti con l'email, token, consensi, log. Per questo il test cerca ovunque.
- Mettere dati personali nei log o nell'audit: il log diventa un secondo database di dati personali, difficile da pulire.
- Chiedere dati "per sicurezza" che poi non usi: ogni dato in più è un rischio e un obbligo.
- La cancellazione non si può annullare: l'interfaccia deve dirlo chiaramente.
- Il periodo di 10 anni per i pagamenti è una scelta da confermare con un professionista. Il codice lo rende facile da cambiare, ma non sappiamo noi qual è quello giusto.

## Come lo spiegheresti a un colloquio

"Ho progettato la privacy come funzionalità: raccolgo meno dati possibile, per esempio un flag maggiorenne invece della data di nascita. Il consenso dei genitori è registrato con la versione dell'informativa. Un genitore può scaricare un JSON con tutto ciò che lo riguarda e può cancellare il proprio account. La cancellazione anonimizza sul posto, così i pagamenti dello studio restano e i totali tornano. Un test cerca nel database il nome e l'email della persona cancellata, e un task notturno applica i tempi di conservazione."

## Domande di autoverifica

1. **Perché anonimizziamo invece di cancellare a cascata?**
   Perché lo studio deve conservare i pagamenti. Si toglie il nome e si tengono importi e date.

2. **Come decide l'esportazione quali dati mostrare?**
   Dal ruolo dell'utente autenticato: un genitore riceve i figli collegati a lui, uno studente adulto solo sé stesso. Nessun id arriva dalla richiesta.

3. **Cosa succede se un figlio ha due genitori e uno chiede la cancellazione?**
   Il figlio resta, perché un altro genitore è collegato, e l'insegnante riceve una email che dice che un genitore se n'è andato.

4. **Perché non salviamo la data di nascita?**
   Perché è un dato in più e cambia ogni giorno. Un sì/no sulla maggiore età basta per decidere chi può avere un account.

5. **Come ci accorgiamo se una tabella nuova conserva dati di una persona cancellata?**
   Il test di cancellazione cerca nome ed email in tutte le colonne di testo del database.
