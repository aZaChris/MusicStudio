# Risorse occupate dallo stack — misure

Misure del 10 novembre 2026, per decidere su quale server pubblicare MusicStudio. Sono misure locali, non del server finale: lo script `scripts/measure-resources.sh` serve a rifarle sul server vero dopo il deploy.

## Dove sono state fatte

- Portatile, WSL2, AMD Ryzen 5 PRO 3500U (8 thread), circa 2,7 GB di RAM. Senza Docker: i processi girano direttamente.
- Backend con i **settings di produzione**, gunicorn con 3 worker (il default del compose di Coolify), cache in memoria al posto di Redis (Redis non è installato qui).
- PostgreSQL 16 con un database realistico: `seed_loadtest`, cioè 10 studi, 50 insegnanti, 1.500 allievi, 1.500 genitori, 78.000 lezioni.
- Memoria misurata come **PSS**: la memoria condivisa tra processi è divisa tra loro, così la somma non la conta due volte.

## Risultati

| Componente | A riposo | Sotto carico (picco) |
| --- | --- | --- |
| gunicorn, master + 3 worker | 204 MB | 242 MB |
| PostgreSQL, tutti i processi | 62 MB | 98 MB |

Carico: 10 utenti simulati con Locust, entrati uno ogni due secondi, per 2 minuti. 436 richieste, 0 errori, mediana 73 ms. Il p95 è 2,2 secondi perché comprende i login: su questa CPU un login costa circa 2 secondi di calcolo (PBKDF2, voluto). CPU media consumata: gunicorn 0,59 core, PostgreSQL 0,01 core.

Un primo tentativo con 20 utenti entrati in 10 secondi ha dato il 14% di errori e latenze di 30 secondi: 20 login quasi insieme saturano i 3 worker. È la "tempesta di login" già descritta nel load test della fase 4; nell'uso reale i login sono rari, perché la sessione si rinnova da sola per 14 giorni.

Altre dimensioni:

- **Database**: 36 MB con 78.000 lezioni. Il dump compresso è circa 1,8 MB (prova di ripristino della fase 4).
- **Portale web**: 412 kB in tutto; il JavaScript è 381 kB, 117 kB compressi con gzip.

## Cosa non è stato misurato qui

Redis, il worker e il beat di Celery, nginx del portale, i sidecar dei backup e le dimensioni delle immagini Docker: senza Docker non si possono avviare come in produzione. Lo script li misura sul server.

## Una stima prudente, da verificare

Sommando le misure, backend e database stanno sotto i 350 MB. Per Redis, Celery, nginx e i backup non abbiamo numeri: per questo un server con **2 GB di RAM** ci sembra un minimo prudente, ma è una stima, non una misura. La conferma arriva da `scripts/measure-resources.sh` dopo il primo deploy.

## Come rifare le misure sul server

```bash
scripts/measure-resources.sh            # tutti i container
scripts/measure-resources.sh backend    # solo quelli con "backend" nel nome
```

Lo script è di sola lettura: mostra CPU, RAM e disco dell'host, `docker stats` dei container, le dimensioni delle immagini e dei volumi, e la dimensione del database.
