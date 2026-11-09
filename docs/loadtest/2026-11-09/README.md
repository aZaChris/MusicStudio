# Load test baseline — 2026-11-09

Primo load test di MusicStudio. Serve come punto di confronto per le modifiche future. I numeri dipendono dalla macchina: vanno confrontati solo con run fatti sulla stessa macchina e con le stesse impostazioni.

## Ambiente

- **Macchina**: portatile, WSL2, AMD Ryzen 5 PRO 3500U (8 thread), circa 2,7 GB di RAM assegnati a WSL. Locust, gunicorn e PostgreSQL girano tutti sulla stessa macchina, quindi si contendono la CPU.
- **Server**: gunicorn con 3 worker sincroni (il default di produzione, `WEB_CONCURRENCY=3`), PostgreSQL 16.15 locale.
- **Settings**: quelli di produzione (`config.settings.prod`), con tre differenze, in un file tenuto fuori dal repository:
  1. cache in memoria per processo invece di Redis, perché Redis non è installato su questa macchina;
  2. limiti di rate alzati: i 50 utenti simulati arrivano tutti dallo stesso IP, e l'obiettivo è misurare la capacità, non i limiti;
  3. nessun redirect HTTPS.
- **Dati**: `manage.py seed_loadtest`: 10 studi, 50 insegnanti, 1.500 allievi, 1.500 genitori, 78.000 lezioni.
- **Scenario** (`backend/loadtest/locustfile.py`): ogni utente è un insegnante o un titolare. Fa il login una volta, poi un'azione ogni 1–3 secondi: calendario della settimana, un'altra settimana, prossime lezioni, dashboard, pacchetti, allievi, e ogni tanto il rinnovo del token.
- **Durata**: 50 utenti, 5 minuti per run.

## Risultati

Tempi in millisecondi. Nessun errore in entrambi i run.

### Run 1 — rampa veloce (5 utenti al secondo): `run_stats.csv`

6.875 richieste, 21,7 richieste al secondo, 0 errori.

- Calendario della settimana: mediana 44, p95 86
- Altra settimana: mediana 44, p95 110
- Prossime lezioni: mediana 30, p95 62
- Dashboard: mediana 21, p95 86
- Pacchetti: mediana 39, p95 87
- Allievi: mediana 48, p95 100
- Rinnovo token: mediana 73, p95 120
- **Login: mediana 7.100, p95 12.000**

### Run 2 — rampa lenta (1 utente al secondo): `run-ramp1_stats.csv`

6.500 richieste, 20,5 richieste al secondo, 0 errori.

- Calendario della settimana: mediana 80, p95 430
- Altra settimana: mediana 80, p95 450
- Prossime lezioni: mediana 56, p95 400
- Dashboard: mediana 39, p95 420
- Pacchetti: mediana 71, p95 400
- **Allievi: mediana 88, p95 560**
- Rinnovo token: mediana 120, p95 540
- Login: mediana 960, p95 1.600

## Verdetto rispetto all'obiettivo (SC-005)

L'obiettivo era: con 50 utenti, p95 sotto 500 ms sulle letture principali ed errori sotto l'1%.

- **Errori**: 0% in entrambi i run. Raggiunto.
- **Letture**: raggiunto nel run 1 (p95 tra 62 e 110 ms). Nel run 2 è raggiunto per quasi tutti gli endpoint, ma **mancato per l'elenco allievi** (p95 560 ms) e per il rinnovo del token (540 ms).
- La differenza tra i due run, con lo stesso throughput, è grande: le mediane quasi raddoppiano. Su un portatile in WSL, con client e server sulla stessa CPU, questa variabilità è normale. Da due run non si può dire se `/students/` sia davvero lento o se il run 2 sia capitato in un momento di carico della macchina. Va rimisurato su un server vero.

## Cosa abbiamo imparato

1. **Il login è limitato dalla CPU.** Una sola richiesta di login, a server fermo, impiega circa 2 secondi: l'hash PBKDF2 di Django è lento apposta, per rendere costoso indovinare le password. Con 3 worker sincroni, il server regge circa 1,5 login al secondo. Nel run 1 arrivavano 5 login al secondo: si sono messi in coda (p95 di 12 secondi) e per qualche secondo hanno bloccato anche le letture. Il p99 di alcune letture nel run 1 (fino a quasi 7 secondi per allievi e altra settimana) viene da lì. È accettabile per l'uso reale, perché il login avviene una volta ogni due settimane e poi si usa il refresh token. Da tenere a mente se un giorno tutti gli utenti di una scuola fanno login nello stesso minuto.
2. **Le letture reggono bene.** Grazie ai budget di query delle fasi precedenti, nessun endpoint fa un numero di query che cresce con i dati, anche con 78.000 lezioni.

## Run scartati

Due run in più sono stati eseguiti e scartati, e i loro file cancellati:

- un run identico al run 2 durante il quale, per errore, ho lanciato i test sulla stessa macchina: la CPU era condivisa e i tempi non erano attendibili;
- una ripetizione del run 2 durante la quale il computer è andato in sospensione per quasi due ore: al risveglio gunicorn ha ucciso i worker per timeout.

## Come ripetere il test

Il seed va fatto con **gli stessi settings del server**. Gli hash delle password dipendono da `PASSWORD_HASHERS`: con i settings di test si usa MD5, che i settings di produzione rifiutano, e ogni login risponde 401. È successo durante questo test.

```bash
cd backend
uv run python manage.py seed_loadtest --i-know-this-is-not-production
uv run --group load locust -f loadtest/locustfile.py --headless \
    -u 50 -r 1 -t 5m --host http://localhost:8000 --csv ../docs/loadtest/<data>/run
```
