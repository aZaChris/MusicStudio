# ADR-M004: Errori visibili e niente retry sui 4xx

- Stato: accettato
- Data: 2026-11-09

## Contesto

Nell'app ereditata un errore del server spariva: la schermata restava vuota, o il pulsante tornava normale senza dire niente. React Query, per default, riprova tre volte ogni richiesta fallita, anche un 403 o un 404 che non cambieranno.

## Decisione

- Ogni risposta non riuscita diventa un `ApiError` con stato, `detail`, `code` ed errori per campo. Stato 0 vuol dire server non raggiungibile.
- `errorMessage()` traduce l'errore in un messaggio nella lingua dell'utente: rete, sessione scaduta, permesso negato, non trovato, troppi tentativi, errore del server; per 400 e 409 mostra il motivo dato dal server.
- Politica di React Query: nessun retry per i 4xx, al massimo due per rete e 5xx, nessun retry per le scritture.
- Un componente `QueryState` mostra in modo uniforme caricamento, errore con "Riprova" e lista vuota.
- Le liste caricano tutte le pagine (`fetchAllPages`). È un limite consapevole, giusto per 1–10 insegnanti; se le liste crescono si passa allo scroll infinito.

## Alternative scartate

- **Gestire gli errori schermata per schermata**: è come erano nati i silenzi dell'app ereditata.
- **Lo scroll infinito subito**: più codice, e per uno studio di musica le liste sono corte.

## Conseguenze

- Ogni schermata ha test per caricamento, errore, lista vuota e dati.
- Un 403 si vede subito, con una sola richiesta: un test lo verifica.
