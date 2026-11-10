# Build fallita su Coolify: variabili vuote iniettate come argomenti di build

## Sintomo

Il primo deploy su Coolify falliva durante la build dell'immagine del backend, al passo `collectstatic` del Dockerfile. Il riassunto del log diceva solo "exit code 1". In locale lo stesso passo funzionava, anche con un checkout pulito e solo le dipendenze di produzione.

## Causa radice

Coolify aggiunge al Dockerfile una dichiarazione `ARG` per **ogni** variabile d'ambiente della risorsa, comprese quelle lasciate vuote. Durante la build, un `ARG` è visibile ai comandi `RUN` come variabile d'ambiente. Così `collectstatic`, che importa i settings di produzione, trovava `TRUSTED_PROXY_COUNT` uguale a stringa vuota. `env.int()` provava a convertire `''` in un numero e andava in errore: `ValueError: invalid literal for int() with base 10: ''`.

In locale la variabile non esisteva proprio, quindi valeva il default e tutto funzionava.

Lo stesso problema si è ripresentato all'avvio. Coolify passa le variabili della risorsa a **tutti** i container. Il `backend` riceveva `TRUSTED_PROXY_COUNT` con il default del compose (`${TRUSTED_PROXY_COUNT:-1}`), mentre `worker` e `beat` la ricevevano vuota così com'era: crash a ogni avvio, stato "Restarting".

## Come l'abbiamo confermata

- Il traceback completo si vede solo con "Show Debug Logs" attivo in Coolify; il log mostra anche la riga "Added N ARG declarations to Dockerfile".
- Riprodotto in locale aggiungendo `TRUSTED_PROXY_COUNT=` (vuota) all'ambiente del comando: stesso `ValueError`.
- Con la correzione, stesso comando con la variabile vuota: 154 file copiati, nessun errore.

## Risoluzione

Nel Dockerfile, il passo `collectstatic` parte da un ambiente vuoto con `env -i` e riceve solo i valori finti dichiarati lì:

```dockerfile
RUN env -i PATH=/usr/local/bin:/usr/bin:/bin \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    DJANGO_SECRET_KEY=build-only ... \
    /opt/venv/bin/python manage.py collectstatic --noinput
```

La build non dipende più da cosa c'è configurato nella piattaforma.

Per l'avvio, la correzione è alla radice: in `config/settings/base.py` una variabile vuota viene tolta dall'ambiente prima di leggere i settings, quindi vale come non impostata e si usa il default. Il test `config/tests/test_empty_env_vars.py` carica i settings di produzione con variabili vuote: fallisce senza la correzione, passa con.

## Lezione per il futuro

- Un passo di build deve dipendere solo da ciò che il Dockerfile dichiara. Le piattaforme possono iniettare variabili che non ti aspetti.
- "Variabile assente" e "variabile vuota" sono due casi diversi: il default copre solo il primo.
- Quando un log dice solo "exit code 1", cerca la modalità di log completa prima di fare ipotesi.
- Le variabili segrete in Coolify vanno marcate come solo runtime (non "build variable"), così non entrano nella build.

## Riferimenti

- `backend/Dockerfile` (passo `collectstatic` nello stage `builder`)
- `backend/config/settings/base.py` (`TRUSTED_PROXY_COUNT`)
- `docs/operations/runbook.md` (primo deploy)
