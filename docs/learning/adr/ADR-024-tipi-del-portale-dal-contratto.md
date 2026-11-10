# ADR-024: I tipi del portale web generati dal contratto

- Stato: accettato
- Data: 2026-11-10

## Contesto

Il portale aveva le interfacce delle risposte scritte a mano. Nel refactor del mobile, generare i tipi dal contratto ha fatto emergere tre errori nel contratto stesso (campi nullabili non dichiarati, un'azione con il tipo sbagliato). Il portale vive sullo stesso branch del backend, quindi il contratto è lì accanto.

## Decisione

- `openapi-typescript@7.13.0`, lanciato con `npx` a versione fissata, genera `frontend/src/api/schema.d.ts` direttamente da `backend/openapi.yaml`. Il generatore non è una dipendenza del portale: chiede TypeScript 5, il portale usa la 6.
- `npm run api:check` rigenera il file e fallisce se è diverso da quello committato. Gira in CI.
- `src/api/types.ts` dà nomi corti ai tipi. Le interfacce scritte a mano sono state tolte, e con loro un hook mai usato.
- Nessuna copia del contratto: a differenza del mobile, che sta su un altro branch.

## Alternative scartate

- **Tipi scritti a mano**: il problema da risolvere.
- **Una copia del contratto nel portale**: inutile sullo stesso branch, e una cosa in più da tenere allineata.
- **Generatori di client completi** (orval): molto codice generato, difficile da rivedere.

## Conseguenze

- Un cambio del contratto che il portale non ha recepito fa fallire la CI.
- Chi modifica un serializer del backend rigenera `openapi.yaml` e poi i tipi del portale: due comandi, documentati nel README.
