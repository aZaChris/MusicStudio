# ADR-M001: Il refactor mobile parte dal branch `app`

- Stato: accettato
- Data: 2026-11-09

## Contesto

Il progetto ha tre linee storiche: `web` (Next.js), `app` (Expo, scritta per le API di `web`) e `refactor/production-standards` (il backend Django rifatto con standard di produzione). Il backend che manteniamo oggi è Django. L'app di `app` non riesce nemmeno a fare il login contro Django: chiama `/auth/login` e si aspetta un solo token.

## Decisione

Il nuovo branch `refactor/mobile` nasce dal commit `3fb9be8` di `app`. Si tengono interfaccia, rotte, tema, traduzioni e componenti. Si riscrive lo strato dati: client HTTP, sessione, tipi, query. Il branch `app` non si tocca. Prima del codice c'è un audit (`docs/learning/audit-iniziale.md`), come per il backend.

## Alternative scartate

- **Un progetto Expo nuovo da zero**: niente "prima" da confrontare, e si rifarebbe un'interfaccia che funziona già.
- **Una cartella `mobile/` dentro il branch del backend**: due constitution e due toolchain nello stesso branch, e la constitution del backend dice che i client sono fuori perimetro.

## Conseguenze

- Il caso studio ha la stessa forma del backend: punto di partenza, audit, refactor documentato.
- Backend e app stanno su branch diversi. Il contratto OpenAPI fa da ponte (ADR-M002).
