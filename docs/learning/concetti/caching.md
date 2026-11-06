# Caching: chiavi versionate e invalidazione

## TL;DR

Una cache conserva il risultato di un calcolo costoso per riusarlo senza rifarlo. La parte difficile non è salvare: è capire quando il dato salvato non è più valido. In MusicStudio la dashboard di insegnanti e titolari è in cache su Redis. Ogni studio ha un numero di versione dentro la chiave, e qualsiasi modifica ai dati dello studio incrementa la versione. Testando un guasto di Redis abbiamo scoperto che il rate limiting faceva cadere tutta l'API, e l'abbiamo corretto.

## Il problema reale

La dashboard è la prima schermata che un insegnante apre, più volte al giorno. Costa sei query. I dati invece cambiano poco: qualche lezione completata, qualche pagamento. Ricalcolare tutto a ogni apertura è lavoro sprecato.

Ma una cache sbagliata è peggio di nessuna cache. Se l'insegnante completa una lezione e la dashboard mostra ancora il vecchio numero di lezioni rimaste nel pacchetto, l'applicazione sembra rotta. C'è una frase famosa: "nell'informatica ci sono solo due cose difficili, invalidare la cache e dare un nome alle cose".

## Come funziona

Pensa alla bacheca degli avvisi di una scuola. Qualcuno scrive l'orario della settimana e lo appende. Tutti lo leggono senza chiedere in segreteria: è la cache. Il problema è quando l'orario cambia. Puoi andare a cercare ogni copia per toglierla, ma è facile dimenticarne una. Oppure puoi numerare le versioni: "orario versione 7". Quando cambia qualcosa, la segreteria annuncia "ora vale la versione 8". Le copie vecchie restano appese, ma nessuno le guarda più, e prima o poi vengono buttate.

Questa è l'idea delle **chiavi versionate**. Il numero di versione fa parte della chiave della cache. Invalidare significa solo incrementare il numero: tutte le chiavi vecchie diventano irraggiungibili in un colpo solo, senza sapere quante e quali sono. Le voci vecchie scadono da sole grazie alla durata (TTL).

Altri concetti utili.

**TTL (time to live).** Quanto a lungo una voce resta in cache. Limita i danni se un'invalidazione viene saltata.

**Cache-aside.** Il codice prima guarda in cache. Se non trova (cache miss), calcola, salva e restituisce.

**Invalidazione dopo il commit.** Se invalidi prima che la transazione sia confermata, un'altra richiesta può ricalcolare la cache leggendo i dati vecchi e salvarla con la versione nuova.

**La cache non deve diventare un punto unico di guasto.** Se Redis non risponde, l'applicazione deve funzionare lo stesso, solo più lenta.

## Come lo abbiamo applicato in MusicStudio

**La cache della dashboard** è in `backend/apps/lessons/cache.py`. La chiave contiene studio, versione dello studio, ruolo, insegnante e data:

```python
key = ":".join(str(p) for p in (
    "dashboard:v1", ctx.studio_id, studio_version(ctx.studio_id),
    ctx.role, ctx.teacher_id, timezone.localdate(),
))
```

La data c'è perché "questa settimana" cambia a mezzanotte. Il TTL è di 5 minuti.

**L'invalidazione** è in `backend/apps/common/signals.py`. I segnali `post_save` e `post_delete` su lezioni, pacchetti, pagamenti e allievi incrementano la versione dello studio, dopo il commit. Ho scelto i segnali perché catturano ogni modo di scrivere: i service, l'admin di Django, la cancellazione via API. Chiamate esplicite nei service avrebbero saltato l'admin.

**Le dashboard dei genitori** non vanno in cache: un genitore può avere figli in più studi e la apre raramente.

**I numeri.** Con la cache calda, una richiesta di dashboard costa **una query** (il contesto del tenant) invece di sei. I test in `backend/apps/lessons/tests/test_dashboard_cache.py` verificano che una scrittura nello studio renda fresca la dashboard successiva, che una scrittura in un altro studio non la tocchi, e che completare una lezione la invalidi.

**Il problema scoperto testando il guasto.** Ho scritto un test che simula Redis spento. La dashboard ricadeva correttamente sul calcolo. Ma la richiesta rispondeva 500 lo stesso. Il motivo: il rate limiting di DRF tiene i contatori nella stessa cache, e con Redis giù sollevava un errore a ogni richiesta. **Un guasto della cache avrebbe fatto cadere tutta l'API.** Ora `backend/apps/common/throttling.py` contiene classi di throttling che "falliscono aperte": se la cache non risponde, la richiesta passa e l'errore va nel log. È un compromesso: durante un guasto di Redis non c'è rate limiting, nemmeno sul login. Ho preferito la disponibilità, e il guasto è visibile nei log e in `/health/ready/`.

**Il test dei budget di query** in `backend/apps/common/tests/test_num_queries.py` ora svuota la cache prima di ogni misura, perché deve misurare il calcolo, non la cache.

## Alternative considerate

**Cancellare le chiavi a ogni scrittura.** Bisognerebbe conoscere tutte le combinazioni di ruolo, insegnante e data. Facile dimenticarne una.

**Solo una durata breve, senza invalidazione.** Dati vecchi fino alla scadenza dopo ogni modifica.

**Chiamate di invalidazione nei service.** Più esplicite dei segnali, ma l'admin e la cancellazione via DRF le salterebbero.

**`cache_page` di Django.** Mette in cache la risposta per URL. Con l'autenticazione è pericolosa: la stessa URL ha contenuti diversi per utenti diversi.

## Errori comuni e trade-off

- **Invalidare prima del commit.** Un'altra richiesta può rimettere in cache i dati vecchi.
- **Dimenticare che `update()` e `bulk_create()` non inviano segnali.** Oggi non è un problema, perché la scalatura del pacchetto avviene insieme al salvataggio della lezione. Ma va ricordato.
- **Mettere in cache oggetti del modello.** Meglio i dati già serializzati: più leggeri e senza sorprese.
- **Chiavi che non includono il tenant.** Un insegnante vedrebbe la dashboard di un altro.
- **Lasciare che la cache faccia cadere l'applicazione.** È esattamente il bug che il test ha trovato.

## Come lo spiegheresti a un colloquio

Ho messo in cache la dashboard con chiavi versionate per studio. La chiave contiene un numero di versione, e i segnali `post_save` e `post_delete` lo incrementano dopo il commit per ogni scrittura su lezioni, pacchetti, pagamenti e allievi. Così invalido tutte le chiavi dello studio in un colpo solo, senza sapere quali esistono, e catturo ogni percorso di scrittura, admin compreso. Una richiesta servita dalla cache costa una query invece di sei. Testando Redis spento ho scoperto che il rate limiting di DRF faceva rispondere 500 a tutta l'API, quindi l'ho reso "fail open", accettando consapevolmente di non avere rate limiting durante un guasto.

## Domande di autoverifica

1. **Cos'è una chiave versionata?**
   Una chiave di cache che contiene un numero di versione. Incrementando la versione, tutte le chiavi vecchie diventano irraggiungibili.

2. **Perché l'invalidazione avviene dopo il commit?**
   Perché prima del commit un'altra richiesta potrebbe ricalcolare la cache con i dati vecchi e salvarla con la versione nuova.

3. **Perché abbiamo usato i segnali invece di chiamate nei service?**
   Perché i segnali scattano su ogni percorso di scrittura dell'ORM, compresi l'admin e la cancellazione via API.

4. **Quale limite hanno i segnali?**
   `QuerySet.update()` e `bulk_create()` non li inviano.

5. **Cosa succedeva con Redis spento, e come l'abbiamo risolto?**
   Il rate limiting di DRF sollevava un errore a ogni richiesta e l'API rispondeva sempre 500. Ora i throttle falliscono aperti: lasciano passare la richiesta e scrivono l'errore nel log.
