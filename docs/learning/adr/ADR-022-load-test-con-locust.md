# ADR-022: Load test con Locust

- Stato: accettato
- Data: 2026-11-09

## Contesto

Fino alla fase 3 sapevamo che ogni endpoint fa un numero fisso di query, grazie ai budget nei test. Ma non sapevamo quante richieste regge il server, né quale parte cede per prima quando gli utenti aumentano. Senza una misura, ogni affermazione sulle prestazioni è un'opinione.

## Decisione

- **Locust**, in un gruppo di dipendenze separato (`load`): non entra nell'immagine Docker né nella CI.
- Lo scenario sta in `backend/loadtest/locustfile.py`, scritto in Python come il resto del progetto. Simula insegnanti e titolari che fanno il login una volta e poi usano le letture principali, con un'azione ogni 1–3 secondi.
- I dati si creano con `manage.py seed_loadtest`: 10 studi, 50 insegnanti, 1.500 allievi, 78.000 lezioni. Il comando usa inserimenti in blocco e si rifiuta di girare con `DEBUG=False` senza un flag esplicito, perché crea migliaia di account con una password nota.
- I risultati di ogni campagna si salvano in `docs/loadtest/<data>/`: i CSV di Locust e un README che descrive la macchina, le differenze rispetto alla produzione, i numeri e il verdetto.
- Obiettivo: 50 utenti, p95 sotto 500 ms sulle letture, errori sotto l'1%. Se l'obiettivo non viene raggiunto, si scrive, non si nasconde.

## Alternative scartate

- **k6**: ottimo, ma gli scenari si scrivono in JavaScript e serve un altro runtime.
- **JMeter**: pesante, configurazione in XML, poco adatto a un progetto piccolo.
- **ab o wrk**: misurano bene una singola URL, ma non sanno fare un login e poi usare il token.

## Conseguenze

- Il primo baseline (2026-11-09) è stato misurato su un portatile, con client e server sulla stessa CPU e senza Redis. È utile per trovare problemi evidenti, non per promettere numeri. Va ripetuto sul server Coolify.
- Il test ha mostrato che il login è limitato dalla CPU: circa 2 secondi per hash su quella macchina, quindi circa 1,5 login al secondo con 3 worker. È il prezzo di PBKDF2, ed è voluto. Le letture sono rimaste tra 62 e 560 ms di p95, con zero errori.
- Il seed deve girare con gli stessi settings del server, perché gli hash delle password dipendono da `PASSWORD_HASHERS`.
