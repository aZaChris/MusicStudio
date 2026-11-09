# Load testing: misurare quanto regge l'API

## TL;DR

Un load test simula molti utenti insieme e misura tempi di risposta ed errori. In MusicStudio abbiamo usato Locust con 50 insegnanti simulati su 78.000 lezioni. Zero errori, letture con un p95 tra 62 e 560 millisecondi a seconda del run. E una scoperta: il login è limitato dalla CPU, perché l'hash delle password è lento apposta. Il documento racconta anche gli errori di misura che abbiamo fatto, perché fanno parte del metodo.

## Il problema reale

I test automatici dicono che il codice è corretto. I budget di query della fase 1 dicono che ogni endpoint fa un numero fisso di query. Ma nessuno dei due dice quante persone possono usare l'app insieme, né quale parte cede per prima.

Senza una misura, ogni frase sulle prestazioni è un'opinione. "Regge tranquillamente" non vuol dire niente a un colloquio. "Con 50 utenti e 78.000 lezioni, il p95 delle letture è sotto i 500 millisecondi, con zero errori" invece sì.

## Come funziona

Pensa alla prova generale di un ristorante prima dell'apertura. Inviti 50 amici, ognuno ordina con il suo ritmo, e misuri quanto aspettano i piatti. Non ti interessa il tempo medio: ti interessa che quasi nessuno aspetti troppo. E scopri dove si forma la coda. Magari la cucina è veloce, ma c'è una sola cassa.

Un load test fa la stessa cosa con le richieste HTTP. Concetti da conoscere:

- **Utenti virtuali**: ognuno segue uno scenario, con una pausa tra un'azione e l'altra.
- **Throughput**: richieste al secondo servite.
- **Percentili**: il **p95** è il tempo entro cui arriva il 95% delle risposte. La media nasconde le attese lunghe; il p95 e il p99 le mostrano.
- **Rampa**: quanto velocemente si aggiungono gli utenti all'inizio.

## Come lo abbiamo applicato in MusicStudio

**Lo strumento.** Locust, in un gruppo di dipendenze separato (`load`), quindi non entra nell'immagine né nella CI. Lo scenario è in `backend/loadtest/locustfile.py`:

```python
class StaffUser(HttpUser):
    wait_time = between(1, 3)

    @task(4)
    def week_calendar(self):
        self.client.get("/api/v1/lessons/", name="GET /lessons/ (this week)")
```

Ogni utente fa il login una volta, poi un'azione ogni 1–3 secondi: calendario, dashboard, pacchetti, allievi, rinnovo del token. I pesi (`@task(4)`) rendono il calendario più frequente delle altre azioni.

**I dati.** Il comando `manage.py seed_loadtest` crea 10 studi, 50 insegnanti, 1.500 allievi e 78.000 lezioni con inserimenti in blocco. Si rifiuta di girare in produzione senza un flag esplicito.

**L'ambiente.** Un portatile in WSL, con client, server e database sulla stessa CPU. Gunicorn con 3 worker, come in produzione. Redis non c'era, quindi la cache era in memoria per processo. I limiti di rate erano alzati, perché i 50 utenti arrivano tutti dallo stesso IP. Tutto è scritto nel report `docs/loadtest/2026-11-09/README.md`.

**I risultati.** Due run validi, 5 minuti ciascuno, zero errori.

- Run 1, rampa di 5 utenti al secondo: letture con p95 tra 62 e 110 ms.
- Run 2, rampa di 1 utente al secondo: letture con p95 tra 400 e 560 ms. L'elenco allievi supera di poco l'obiettivo di 500 ms.

La differenza tra i due run è grande, con lo stesso throughput. Su un portatile, con client e server che si contendono la CPU, è normale. Per questo il verdetto è prudente: obiettivo raggiunto in un run e mancato per un endpoint nell'altro, da rimisurare su un server vero.

**La scoperta: il login.** Un login, a server fermo, impiegava circa 2 secondi. Django salva le password con PBKDF2 e un milione di iterazioni, apposta lento per rendere costoso indovinarle. Con 3 worker sincroni, il server regge circa 1,5 login al secondo. Nel run 1 i login arrivavano a 5 al secondo: si sono messi in coda fino a 12 secondi, e per qualche istante hanno bloccato anche le letture. Nell'uso reale non è un problema, perché il login avviene una volta ogni due settimane. Ma è un dato da conoscere.

**Gli errori di misura.** Ne abbiamo fatti tre, e li abbiamo scritti nel report.

1. Il primo run ha dato 401 su ogni login. Il seed era stato fatto con i settings di test, che usano l'hash MD5 per velocità; i settings di produzione non lo riconoscono. Il seed va fatto con gli stessi settings del server.
2. Un run è stato contaminato: mentre girava, ho lanciato i test sulla stessa macchina. Scartato.
3. Durante un altro run il computer è andato in sospensione per quasi due ore. Al risveglio gunicorn ha ucciso i worker. Scartato anche questo.

## Alternative considerate

**k6.** Molto usato, ma gli scenari si scrivono in JavaScript. Locust è Python, come il resto del progetto.

**JMeter.** Potente, ma pesante e configurato in XML.

**ab o wrk.** Ottimi per bombardare una URL, ma non sanno fare un login e usare il token.

## Errori comuni e trade-off

- **Guardare la media.** Una media di 100 ms può nascondere un 5% di utenti che aspettano 10 secondi.
- **Testare su dati vuoti.** Con 10 lezioni tutto è veloce. Servono volumi realistici.
- **Client e server sulla stessa macchina.** Si rubano la CPU a vicenda. Va dichiarato, e i numeri vanno presi con cautela.
- **Non raccontare i run falliti.** Un run scartato in silenzio rende il report meno credibile, non più bello.
- **Trade-off:** un test su un portatile trova i problemi evidenti, come la coda dei login, ma non promette numeri per la produzione.

## Come lo spiegheresti a un colloquio

Ho scritto un load test con Locust che simula 50 insegnanti su 78.000 lezioni, con login, calendario, dashboard e rinnovo del token. Su un portatile ho avuto zero errori e un p95 delle letture tra 62 e 560 millisecondi, con una variabilità tra i run che ho dichiarato invece di nascondere. La scoperta principale è stata il login: l'hash PBKDF2 costa circa 2 secondi di CPU su quella macchina, quindi una raffica di login satura i 3 worker e rallenta anche le letture. Nell'uso reale va bene, perché il login avviene ogni due settimane. Ho anche documentato gli errori di misura, come il seed fatto con un hasher diverso da quello del server.

## Domande di autoverifica

1. **Perché il p95 è più utile della media?**
   Perché mostra quanto aspettano gli utenti più sfortunati. La media può essere bassa anche se una parte degli utenti aspetta molto.

2. **Perché il login era così lento?**
   Perché PBKDF2 è progettato per essere costoso: rende lento indovinare le password. Con poca CPU e 3 worker, i login si mettono in coda.

3. **Perché tutti i login davano 401 nel primo tentativo?**
   Perché il seed aveva salvato le password con l'hash MD5 dei settings di test, che i settings di produzione non accettano.

4. **Perché abbiamo alzato i limiti di rate durante il test?**
   Perché tutti gli utenti simulati arrivavano dallo stesso IP. Volevamo misurare la capacità del server, non i limiti.

5. **Perché il verdetto sul p95 è prudente?**
   Perché i due run validi danno numeri molto diversi, su una macchina dove client e server condividono la CPU. Serve una misura su un server vero.
