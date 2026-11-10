# KB: I test del portale fallivano o non partivano su una macchina con poca RAM

## Sintomo
La suite di Vitest del portale (48 test) dava a ogni esecuzione risultati diversi: 1 fallimento, poi "38 passed", poi "no tests", con `Failed to start forks worker ... Timeout waiting for worker to respond`.

## Causa radice
Ogni file di test avvia jsdom e renderizza l'app intera. Con il numero predefinito di worker paralleli, una macchina da 2,7 GB non riusciva ad avviarli tutti; quelli lenti superavano anche i timeout predefiniti (1 s per le attese di Testing Library, 5 s per test).

## Come l'abbiamo confermata
Un test isolato passava sempre; il messaggio di errore indicava worker che non partivano; con 2 worker la suite completa è passata due volte di fila.

## Risoluzione
`maxWorkers: 2`, `testTimeout: 30000` in `vite.config.ts`; `asyncUtilTimeout: 10000` nel setup dei test.

## Lezione per il futuro
Un test che passa da solo e fallisce in gruppo spesso non ha un bug di logica: ha un problema di risorse o di tempo. Prima di cambiare il codice, va guardato il messaggio esatto e il carico della macchina.

## Riferimenti
- `frontend/vite.config.ts`, `frontend/src/test/setup.ts`
