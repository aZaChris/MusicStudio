# Movimento

Ogni animazione risponde a una domanda: da dove arriva questa cosa, o che cosa è appena cambiato. Se non risponde a nessuna delle due, non si fa.

## Le sei animazioni

- **Cambio schermata.** Andando avanti, la schermata vecchia esce a sinistra e sfuma, la nuova entra da destra di 24px. Tornando indietro, al contrario. `duration-base`, `ease-out-soft`.
- **Pannello dal basso** (mobile). Sale dal bordo mentre il velo `scrim` sfuma. Si apre in `duration-slow` e si chiude in `duration-base`; si chiude anche trascinandolo giù.
- **Finestra di dialogo** (web). Entra con una dissolvenza e un leggero ingrandimento, da 0.96 a 1. `duration-base`.
- **Battuta che si riempie.** Quando una lezione è completata il suo pallino passa da vuoto a pieno con un rimbalzo: scala 0.6 → 1.2 → 1. `duration-slow`, `ease-bounce`. È l'unico rimbalzo del sistema.
- **Pulsante premuto.** Al tocco si stringe al 96% e torna su, in `duration-fast`. Sul telefono le azioni che salvano danno anche una vibrazione leggera.
- **Cambio di stato.** Un'etichetta che cambia (Programmata → Completata) dissolve nella nuova senza spostare il layout. Da `duration-fast` a 180ms.

## Caricamento

Al posto della rotellina si mostrano sagome della lista (blocchi `line-2` dei bordi arrotondati) con un riflesso lento. I dati arrivano dove l'occhio sta già guardando.

## Riduci movimento

Se il sistema operativo chiede di ridurre il movimento, spostamenti, ingrandimenti e rimbalzi si spengono. Restano solo le dissolvenze, accorciate a `duration-fast`.

## Nel codice

- **App mobile:** le transizioni di Expo Router per le schermate e `react-native-reanimated` per pannello, battute e pulsanti. Funziona in Expo Go.
- **Portale web:** transizioni CSS con i token di durata e curva; View Transitions per il cambio pagina dove il browser le supporta, altrimenti solo la dissolvenza.
