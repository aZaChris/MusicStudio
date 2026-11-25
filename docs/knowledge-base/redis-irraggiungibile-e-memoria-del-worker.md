# KB: Il worker Celery non raggiunge Redis e la RAM sale per colpa di Celery

## Sintomo
Sentry, produzione, 22 novembre 2026 alle 20:51:02 UTC: issue `MUSICSTUDIO-3`. Due eventi nello stesso trace. Il primo è `consumer: Cannot connect to redis://…@redis:6379/0: Error 111 … Connection refused. Trying again in 2.00 seconds... (1/100)`. Il secondo è `Error on restarting Gossip: AttributeError("'NoneType' object has no attribute 'connection_errors'")`. Lo stesso errore si è ripresentato la sera del 24 novembre. Elio ha visto anche picchi di RAM al 72% attribuiti a Celery.

## Causa radice
Ci sono due problemi distinti.

Il primo: Redis per qualche secondo non ascoltava sulla porta 6379. Errno 111, "Connection refused", vuol dire che l'host esiste nella rete Docker ma nessun processo accetta connessioni, cioè il container era fermo o si stava riavviando. L'`AttributeError` su Gossip è solo una conseguenza: è un difetto noto di kombu/celery quando riavvia i componenti con la connessione già persa. Il worker si è riconnesso al primo tentativo (in Sentry c'è solo 1/100).

Perché Redis fosse fermo **non è confermato**. Le ipotesi sono tre:
1. Redis ucciso per memoria. Il container ha `mem_limit 128m` con `maxmemory 96mb`, e il `fork` della riscrittura AOF può superare il limite.
2. Redeploy o riavvio dello stack da Coolify. I container attuali sono stati ricreati il 24 novembre alle 23:07 (lo dice il suffisso `20261124T230723` nei nomi), il che spiega bene l'evento del 24 sera.
3. Riavvio della VPS o di Docker.

Il 22 non c'è stato nessun merge su `main`, quindi non è stato un deploy partito da noi.

Il secondo: la memoria del worker. Celery in modalità prefork (`--concurrency 2`) tiene vivi i processi figli per sempre. Un processo Python con Django cresce e non restituisce memoria al sistema, quindi il worker sale piano piano verso il limite di 512 MB del suo container.

## Come l'abbiamo confermata
Breadcrumb di Sentry in ordine: `PUBLISH worker.offline`, `SREM _kombu.binding.celeryev`, errore Gossip, `PING`, "Connection refused". Nessun commit su `main` tra il 17 e il 24 novembre (`git log`). Configurazione letta in `docker-compose.coolify.yml` e `backend/docker/entrypoint.sh`: nessun riciclo dei figli. La causa del riavvio di Redis aspetta i log del server (`journalctl -k`, `last -x reboot`, Deployment Logs di Coolify), che può controllare solo Elio: gli abbiamo dato una scheda con i comandi.

## Risoluzione
PR #61: in `backend/config/settings/base.py` ci sono `CELERY_WORKER_MAX_TASKS_PER_CHILD` (100) e `CELERY_WORKER_MAX_MEMORY_PER_CHILD` (180000 KB), letti dall'ambiente. Un figlio viene sostituito dopo 100 task o sopra circa 180 MB, ma solo dopo aver finito il task in corso. Il test `test_worker_children_are_recycled_before_the_container_limit` controlla che 2 figli stiano sotto i 512 MB. `REDIS_MEM_LIMIT` resta com'è finché i log del server non mostrano davvero un OOM di Redis.

## Lezione per il futuro
"Connection refused" non è un timeout: dice che il servizio era spento, quindi bisogna cercare chi l'ha spento (OOM, redeploy, riavvio), non problemi di rete. Il timestamp nel nome dei container di Coolify dice quando sono stati ricreati, e dopo un redeploy `docker inspect` e `docker logs` non vedono più il passato: resta solo il log del kernel. Un worker prefork senza riciclo dei figli è una perdita di memoria lenta garantita.

## Riferimenti
- `docs/learning/adr/ADR-016-affidabilita-celery.md` (affidabilità di Celery: acks_late, task idempotenti)
- `docs/knowledge-base/redis-giu-e-throttling.md` (perché l'API regge senza Redis)
- Documentazione di Celery: `worker_max_tasks_per_child`, `worker_max_memory_per_child`
