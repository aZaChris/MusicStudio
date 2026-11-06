# KB: `pre-commit install` rifiuta di installarsi

## Sintomo
`pre-commit install` termina con: "Cowardly refusing to install hooks with `core.hooksPath` set."

## Causa radice
Sulla macchina c'è un `core.hooksPath` globale (`~/.config/git/hooks`) che ospita il `post-commit` della sincronizzazione del vault Obsidian. pre-commit installa i suoi hook in `.git/hooks`, che git ignora quando `core.hooksPath` è impostato, quindi si rifiuta.

## Come l'abbiamo confermata
`git config --get core.hooksPath` restituisce la cartella globale; `ls ~/.config/git/hooks` mostra solo `post-commit`.

## Risoluzione
Hook versionati in `.githooks/`: `pre-commit` esegue `backend/.venv/bin/pre-commit run`, `post-commit` richiama l'hook globale. Attivazione una volta per clone: `git config core.hooksPath .githooks`. Verificato: il commit esegue gli hook e il diario del vault si aggiorna.

## Lezione per il futuro
Con un `core.hooksPath` globale, ogni strumento che installa hook in `.git/hooks` (pre-commit, husky) va collegato a mano, e l'hook locale deve **catenare** quello globale per non perderlo.

## Riferimenti
- `docs/learning/concetti/ci-e-quality-gate.md`
- Documentazione pre-commit, sezione "core.hooksPath"
