# KB: Il filtro di rtk nascondeva un errore di pytest

## Sintomo
Durante la fase 4 l'output dei test riportava "22 passed" e sembrava tutto verde. In realtà un test era in errore.

## Causa radice
rtk riscrive i comandi per ridurre l'output. Il suo filtro per pytest riassume il risultato, e in quel caso ha mostrato i test passati ma non la riga dell'errore.

## Come l'abbiamo confermata
Rilanciando lo stesso comando con `rtk proxy` (output non filtrato): "22 passed, 1 error".

## Risoluzione
Quando il risultato esatto conta, pytest si lancia con `rtk proxy`. La regola è in `CLAUDE.md`.

## Lezione per il futuro
Uno strumento che riassume l'output è comodo, ma un riassunto può tacere proprio la riga che conta. Per i controlli che decidono un commit, serve l'output completo.

## Riferimenti
- `CLAUDE.md`, sezione "Gotchas learned the hard way"
