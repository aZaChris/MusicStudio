# `worker` e `beat` in crash-loop: manca `packaging` nell'immagine

## Sintomo

Sul deploy di staging su Coolify `backend`, `db`, `redis` e `web` erano sani, mentre `worker` e
`beat` restavano in "Restarting". Nei log di entrambi, in fondo al traceback:

```
File ".../kombu/transport/redis.py", line 119, in <module>
    from packaging.version import Version
ModuleNotFoundError: No module named 'packaging'
```

In locale e in CI tutto era verde.

## Causa radice

`kombu` 5.7.0, la libreria con cui Celery parla con Redis, importa `packaging` nel suo
trasporto Redis, ma non lo dichiara tra le sue dipendenze (sono `amqp`, `vine` e `tzdata` solo su
Windows). Nel nostro `uv.lock` `packaging` c'era comunque, ma solo perché lo porta un pacchetto
del gruppo di sviluppo (pytest e simili).

L'immagine di produzione si costruisce con `uv sync --no-dev`, quindi `packaging` non ci finisce.
Il `backend` non usa il trasporto Redis di kombu e parte lo stesso; `worker` e `beat` sì e
muoiono all'avvio.

È la stessa famiglia di [tzdata-sparito-con-kombu.md](tzdata-sparito-con-kombu.md): ci
appoggiavamo a una dipendenza che arrivava per caso.

## Come l'abbiamo confermata

Senza Docker, con due ambienti "di produzione" (`uv sync --frozen --no-dev`):

- con il lock vecchio, `python -c "import kombu.transport.redis"` dà `ModuleNotFoundError`;
- con `packaging` dichiarato, lo stesso comando stampa `ok`.

## Risoluzione

- `packaging>=24` dichiarato tra le dipendenze di `backend/pyproject.toml` (e `uv.lock`).
- Nel `Dockerfile`, subito dopo `uv sync`, `RUN python -c "import kombu.transport.redis"`: se
  manca di nuovo un import a runtime, a fallire è la build, non il deploy.

## Lezione per il futuro

I test e la CI girano con le dipendenze di sviluppo, quindi non vedono ciò che manca all'immagine
di produzione. Un import che funziona in locale non prova che funzioni nell'immagine: la prova
è importarlo con `--no-dev`. Se una libreria importa un pacchetto che non dichiara, lo
dichiariamo noi.

Nota a margine: un backend sano non dimostra che Celery lo sia. Per questo il quickstart
chiede di guardare i log di `worker` e `beat`, non solo lo stato del `backend`.

## Riferimenti

- `backend/pyproject.toml`, `backend/Dockerfile`
- Commit di questa correzione e quickstart, traccia B (`specs/001-musicstudio-mvp/quickstart.md`)
