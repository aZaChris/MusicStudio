# I titoli del tema chiaro non usavano Bricolage Grotesque

## Sintomo

Negli screenshot per il README i titoli del tema chiaro ("Hi, owner", "Giulia Rossi") avevano un
font largo e generico, DejaVu Sans Bold. Gli stessi titoli nel tema scuro usavano Bricolage
Grotesque, il font display del design system. I test (Vitest su jsdom) non lo vedevano, perché
jsdom non applica i fogli di stile.

## Causa radice

Una questione di specificità CSS.

- `tokens.css`, generato dal design system, definisce `--font-display: 'Bricolage Grotesque'`
  con il selettore `:root, :root[data-theme='light']`.
- Il pacchetto `@fontsource-variable/bricolage-grotesque` registra il font con un altro nome,
  `'Bricolage Grotesque Variable'`. Per questo `base.css` ridefiniva la variabile con quel nome,
  ma solo su `:root`.
- `:root[data-theme='light']` ha specificità (0,2,0), `:root` ha (0,1,0). Nel tema chiaro vinceva
  quindi il nome sbagliato, il browser non trovava il font e usava il ripiego `system-ui`.
- Il blocco `:root[data-theme='dark']` non ridefinisce il font. Nel tema scuro restava la
  correzione di `base.css`, che arriva dopo nel bundle e ha la stessa specificità di `:root`.

## Come l'abbiamo confermata

- In un primo momento sembrava una corsa: lo screenshot scattava prima che il font fosse
  caricato. Aspettare `document.fonts.ready` non ha cambiato niente, quindi l'ipotesi era
  sbagliata.
- Il nome del font registrato da fontsource (`grep font-family` nel suo CSS) era diverso da
  quello dei token.
- Le regole che impostano `--font-display` erano due, con selettori di specificità diversa.
- Dopo la correzione, gli screenshot chiari della build di produzione mostrano Bricolage.

## Risoluzione

`frontend/src/theme/base.css` ora ridefinisce la variabile su `:root, :root[data-theme]`, che ha
la stessa specificità del selettore dei token e vince perché arriva dopo nel bundle.

## Lezione per il futuro

- Quando un override di una custom property "funziona in un tema e non nell'altro", confronta i
  selettori, non solo i valori: la specificità vale anche per le variabili CSS.
- Un nome di font sbagliato non dà errori: il browser passa in silenzio al ripiego. Solo un
  controllo visivo lo trova. Gli screenshot del README fanno anche da controllo visivo, in
  entrambi i temi.

## Riferimenti

- `frontend/src/theme/base.css`, `frontend/src/theme/tokens.css`
- `scripts/readme-screenshots.mjs`
- MDN, "Specificity": https://developer.mozilla.org/en-US/docs/Web/CSS/Specificity
