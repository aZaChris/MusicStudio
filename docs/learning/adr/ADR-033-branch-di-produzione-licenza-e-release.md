# ADR-033: Branch di produzione, licenza MIT e una release per fase

- Stato: accettato
- Data: 2026-11-12

## Contesto

Il repository è pubblico ed è un portfolio. Chi lo apre vedeva come branch predefinito
`staging/backend`, più altri tre branch (`staging/mobile`, `refactor/production-standards`,
`refactor/mobile`) che sembravano lavori a metà. I due `refactor/*` erano già interamente
contenuti nei branch di staging. Non c'era una licenza, quindi legalmente il codice era "tutti i
diritti riservati". Non c'erano release: le fasi completate si vedevano solo leggendo i commit.
GitHub non permette di nascondere un branch: si può solo cambiare quello predefinito o
cancellarlo.

## Decisione

- `staging/backend` diventa **`main`**: il branch predefinito e la linea di produzione per API e
  portale web. `staging/mobile` diventa **`mobile`**. Il cambio di nome è fatto con l'API di
  GitHub, che sposta anche il branch predefinito e lascia un redirect dai vecchi nomi.
- `main` e `mobile` sono protetti da un **ruleset**: niente force-push, niente cancellazione, si
  cambiano solo con una **pull request** e la PR si unisce solo con la CI verde (su `main`:
  `backend (postgres 16.15)`, `backend (postgres 18.6)`, `frontend`, `web-image`, `secrets`; su
  `mobile`: `gate`). Le approvazioni richieste sono zero, perché lo sviluppatore è uno solo.
- Le PR sono necessarie per un motivo tecnico, non di forma. Un check obbligatorio senza PR
  rifiuterebbe ogni push diretto: il commit appena spinto non ha ancora i risultati della CI.
  L'unica via d'uscita sarebbe un bypass per l'amministratore, e a quel punto la regola non
  proteggerebbe più niente.
- I branch `refactor/*` diventano tag `archive/refactor-production-standards` e
  `archive/refactor-mobile`, come era già successo per `archive/web` e `archive/app`, e i branch
  vengono cancellati.
- Ogni fase completata ha una **release** con un tag `vX.Y.0` sul commit di chiusura della fase. I
  numeri seguono l'ordine in cui le fasi sono state completate, non il loro numero nella
  roadmap, così la serie non ha buchi.
- Licenza **MIT**.

## Alternative scartate

- **Git flow leggero** (`main` per la produzione, `staging/*` per lo sviluppo, rilasci con PR da
  staging a main): ha senso con più persone o con ambienti separati. Qui raddoppiava i branch da
  tenere allineati senza dare una garanzia in più.
- **Solo cambiare il branch predefinito**: lasciava in vista quattro branch con nomi che
  raccontano la storia del lavoro, non lo stato del progetto.
- **AGPL-3.0**: protegge un prodotto da vendere come servizio. Per un portfolio scoraggia proprio
  chi dovrebbe leggere e riusare il codice.
- **Nessuna licenza**: il codice resta leggibile ma non riutilizzabile, e GitHub non mostra la
  licenza nella pagina del repository.

## Conseguenze

- Chi ha un clone vecchio deve rinominare i branch locali (`git branch -m staging/backend main`,
  poi `git branch -u origin/main`). GitHub lo ricorda con un avviso nella pagina del repository.
- Coolify, se è già configurato, va puntato su `main` invece di `staging/backend`.
- Lo script `contract.mjs` del branch `mobile` legge il contratto OpenAPI da `main`.
- Si lavora su un branch di feature (per esempio quello della fase, `008-…`) e si apre una PR
  verso `main`. Un errore già unito si corregge con una nuova PR, mai riscrivendo la storia.
- I nomi dei check contengono la versione di PostgreSQL della matrice CI. Se la versione cambia,
  va aggiornato anche il ruleset, altrimenti le PR restano in attesa di un check che non arriva.
- La fase 5 (Polish) non ha ancora una release: quando sarà completata prenderà il numero
  successivo all'ultimo.
