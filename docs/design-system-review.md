# Design system MusicStudio: revisione e traduzione in codice

Data: 10 novembre 2026. Fonte: il design system "MusicStudio" su claude.ai (creato oggi, versione
delle 17:56) e il canvas "MusicStudio Design" con tutte le schermate. Questa nota dice cosa è stato
tradotto, dove vive nel codice, cosa ho trovato rivedendolo e cosa ho scelto di non fare.

## Dove sta il design system nel repository

- `design/system/tokens.json`: la fonte unica (colori chiaro e scuro, tipografia, spazi, raggi,
  ombre, durate e curve).
- `design/system/README.md` e `motion.md`: il libro del marchio e le sei animazioni.
- `design/system/components.css`: il kit CSS con le classi `ms-*`.
- Web: `npm run tokens` (in `frontend/`) genera `src/theme/tokens.css` e copia il kit in
  `src/theme/components.css`. Il layout della pagina è in `src/theme/base.css`.
- Mobile (branch `staging/mobile`): `npm run tokens` genera `src/constants/tokens.generated.ts`;
  `src/constants/theme.ts` aggiunge font e stili di testo.

Per cambiare un colore: si modifica `tokens.json` e si lancia `npm run tokens`. Niente più
valori scritti a mano nelle pagine.

## Cosa è stato tradotto

Web: login a due pannelli, barra laterale plum, home con tre schede numero, elenco delle prossime
lezioni con "Completa", studenti come schede con le battute, dettaglio studente, pagamenti con
filtri e modulo, portale genitore con la scheda "Prossima lezione", dialog con velo, caricamento a
sagome, scorrimento di pagina da destra. Font con `@fontsource`, quindi la CSP resta `font-src 'self'`.

Mobile: stesse schermate con le stesse regole. Barra a tab con la pillola arancio sull'icona,
pannello dal basso per "Segna come completata" e per "Registra pagamento" (si apre dal pulsante
flottante), battute che si riempiono con il rimbalzo, pulsanti che si stringono al tocco,
vibrazione leggera quando si salva. Tutto si spegne con "riduci movimento".

## Cosa ho trovato rivedendo il design system

Contrasto, calcolato sui valori di `tokens.json` (soglie WCAG 2.2):

1. `orange-text` su `orange-soft` fa 4.16 a 1 nel tema chiaro. Sotto il 4.5 richiesto per il testo.
   Succede nell'etichetta "In esaurimento" e nel testo della tab attiva. Nel codice l'etichetta
   usa `ink` su `orange-soft` (13.5 a 1). Se si vuole risolvere alla radice, `orange-text` va
   scurito di poco (circa `#a84a14`).
2. Il contorno arancio delle battute vuote è 2.40 a 1 su `paper` e 2.60 a 1 su `card`. Per gli
   elementi non testuali servono 3 a 1. Le battute restano leggibili grazie al riempimento
   `orange-soft`, ma il contorno da solo non basta. Non l'ho cambiato perché è il segno distintivo
   del sistema: è una scelta da fare nel design.
3. `line` su `card` fa 1.32 a 1 (chiaro) e 1.24 a 1 (scuro). Va bene per i separatori, non per il
   bordo dei campi di testo, che dovrebbe arrivare a 3 a 1. Servirebbe un token `field-border`.
   Il campo attivo ha il bordo arancio, quindi il problema è sul campo a riposo.
4. Tutte le altre coppie testo/fondo passano (chiaro e scuro), comprese le coppie di stato.

Coerenza tra canvas e `tokens.json` (il codice segue `tokens.json`):

5. I nomi sono diversi: il canvas usa `--or`, `--ink2`, `--line2`, `--or-text`, i token
   `orange`, `ink-2`, `line-2`, `orange-text`. Il kit CSS usa i nomi dei token, quindi le schermate
   del canvas non si possono incollare così come sono.
6. Nel canvas la barra laterale scura usa `#2C1C36` e la linea `#8A6C99`; i token dicono
   `#3A2547` e `#6E4F7E`. L'ombra del pulsante flottante nel canvas è neutra, nei token è
   arancio. Nel codice valgono i token.
7. Il raggio degli avatar (12, 16, 20, 22 px) non è un token. Nel codice è un rapporto fisso (31%).
8. `motion.md` cita le View Transitions per il web. Ho usato una transizione CSS (24 px da destra)
   che funziona ovunque; le View Transitions si possono aggiungere dopo.
9. Il README elenca nove icone. Servono anche il tema chiaro/scuro e la lingua sul web: li ho
   fatti come pillole di testo, senza inventare icone nuove.

## Scelte fatte nella traduzione

- Web: la griglia della settimana è sostituita dall'elenco "Prossime lezioni" del canvas. Il dato
  `week` dell'API non è più usato. La tabella "Pagamenti recenti" della home non c'è: richiederebbe
  una chiamata in più che oggi la home non fa.
- Web e mobile: niente emoji nei testi (il saluto era "Ciao, Elena 👋"), come chiede il README.
- Mobile: nessun selettore di lingua nel login; la lingua segue il telefono, come prima.
- Mobile: dopo aver registrato un pagamento il pannello resta aperto con la conferma "Pagamento
  registrato." e l'importo svuotato, come faceva il modulo in pagina.
- I test sono stati aggiornati ai nuovi testi e alla nuova struttura. Nessun test è stato rimosso.

## Da decidere

- I tre punti di contrasto (1, 2, 3): correggerli nel design system su claude.ai e rigenerare.
- Se allineare i nomi del canvas a quelli dei token (punto 5).
