# ADR-017: Cache della dashboard con chiavi versionate per studio

- Stato: accettato
- Data: 2026-11-06

## Contesto

La dashboard è la schermata più aperta e costa sei query. I dati cambiano poco rispetto a quante volte viene letta. Ma una dashboard vecchia dopo una modifica (per esempio una lezione appena completata) sarebbe un bug visibile.

## Decisione

- La dashboard di insegnanti e titolari è salvata in Redis per 5 minuti con la chiave `dashboard:v1:<studio>:<versione>:<ruolo>:<insegnante>:<data>`.
- Ogni studio ha un numero di **versione** in cache. Qualsiasi scrittura su lezioni, pacchetti, pagamenti o allievi dello studio lo incrementa, quindi tutte le chiavi vecchie diventano irraggiungibili in un colpo solo e scadono da sole.
- L'incremento avviene con i **segnali** `post_save` e `post_delete`, dopo il commit. I segnali catturano ogni percorso di scrittura: service, admin di Django, `destroy` di DRF.
- Le dashboard dei genitori non vanno in cache: un genitore può avere figli in più studi e la apre raramente.
- **Se la cache non risponde**, la dashboard si calcola normalmente.
- **Throttling che "fallisce aperto"**: testando un guasto di Redis è emerso che i throttle di DRF, che tengono i contatori in cache, facevano rispondere 500 a ogni richiesta. Ora, se la cache non risponde, la richiesta passa e l'errore va nel log.

## Alternative scartate

- **Cancellare le chiavi a ogni scrittura**: bisognerebbe conoscere tutte le chiavi (ruoli, insegnanti, date).
- **Solo una durata breve**: dati vecchi per qualche minuto dopo ogni modifica.
- **Invalidare con chiamate esplicite nei service**: l'admin e `destroy` le salterebbero.
- **`cache_page` di Django**: cache per URL, ignora il tenant. Pericolosa con l'autenticazione.

## Conseguenze

- Una richiesta servita dalla cache costa una query (il contesto del tenant) invece di sei.
- **Limite dei segnali**: `QuerySet.update()` e `bulk_create()` non li inviano. Oggi non è un problema, perché la scalatura del pacchetto avviene insieme al salvataggio della lezione, che il segnale lo invia. Va ricordato per il codice futuro.
- Le parti che dipendono dall'ora ("prossime lezioni") possono essere vecchie fino a 5 minuti.
- Durante un guasto di Redis non c'è rate limiting, nemmeno sul login. È un compromesso a favore della disponibilità, visibile nei log e in `/health/ready/`.
