# MusicStudio

MusicStudio è un gestionale per insegnanti di musica e piccole scuole: lezioni, pacchetti di lezioni, pagamenti e un portale in sola lettura per i genitori. Lo usano un'insegnante tra una lezione e l'altra sul telefono, una titolare di studio alla scrivania, un genitore la sera. Il linguaggio visivo è **caldo e creativo**: caldo come una sala prove, ordinato come un registro.

Il sistema serve due app con lo stesso aspetto: l'app mobile (Expo / React Native) e il portale web (React). Il riferimento visivo completo, con tutte le schermate in tema chiaro e scuro, è il canvas "MusicStudio Design".

## Voce e testi

- Italiano semplice, frasi brevi, tono di chi lavora nella stessa scuola. Inglese come seconda lingua, con lo stesso dizionario.
- Le cose si chiamano come le chiama chi insegna: *lezione*, *pacchetto*, *rimanenti*, *genitore*, mai i nomi tecnici del server.
- I valori che arrivano dall'API si traducono sempre: `paid` → "Pagato", `no_show` → "Assente", `bank_transfer` → "Bonifico". Mai mostrare il valore grezzo.
- I pulsanti dicono cosa succede: "Registra pagamento", "Segna come completata", "Esci". Dopo, una conferma breve: "Pagamento registrato."
- Gli errori dicono cosa è successo e cosa fare: "Email o password non validi.", "Troppi tentativi. Aspetta un minuto e riprova." Niente scuse, niente "Oops".
- Niente emoji nell'interfaccia. Niente punti esclamativi.

## Fondamenta visive

**Colori.** Quattro colori fanno l'identità:
- `paper`, la carta calda di fondo;
- `ink`, l'inchiostro marrone scuro del testo;
- `orange`, l'azione: il pulsante principale, il campo attivo, le battute ancora da usare;
- `plum`, il risalto: il numero più importante di una schermata, la testata del login, il menu web.

Regole:
- Il testo sopra `orange` è sempre `on-orange` (scuro), mai bianco, perché il bianco non passa il contrasto.
- L'arancio usato come testo è `orange-text`, più scuro di `orange`.
- Il contorno delle battute vuote è `beat-edge` (su plum resta `orange`); il bordo dei campi a riposo è `field-border`: entrambi hanno almeno 3:1 su `paper` e `card`.
- Gli stati hanno coppie dedicate fondo/testo (`ok`, `wait`, `bad`, `plan`, `off`) e non si usano per decorare.
- Il tema scuro non è il chiaro invertito: il fondo è un marrone quasi nero caldo, l'arancio si schiarisce un poco e `beat-on` diventa lilla per restare visibile.

**Tipografia.**
- Bricolage Grotesque (famiglia `display`) per titoli, numeri e importi: ha carattere e numeri belli grandi.
- Figtree (famiglia `body`) per tutto il resto.
- I numeri importanti si mostrano grandi, a 44px. Le etichette in maiuscolo (`label`) solo sopra un dato.

**Forme.**
- Tutto è morbido: i pulsanti, i filtri e le etichette sono pillole (`radius-pill`); le schede usano `radius-card`, le righe `radius-row`.
- I bordi sono da 1px (`line`); le ombre solo su ciò che galleggia (`shadow-card`, `shadow-float`), mai sulle schede ferme.

**Spazi.**
- Margine laterale di 20px su mobile e da 16 a 48px sul web.
- Tra le schede `space-3`, tra le sezioni `space-6`.
- I bersagli toccabili sono almeno 44px.

## Il motivo: le battute

Un pacchetto di lezioni si mostra come una fila di **battute**: un pallino per lezione. Pieno (`beat-on`) se la lezione è già stata usata, vuoto con bordo arancio se è ancora da fare. Sotto le 3 rimanenti il pacchetto diventa "In esaurimento" (etichetta `low`) e la home mostra un avviso. Quando una lezione viene completata il suo pallino si riempie con un piccolo rimbalzo. È l'elemento che rende MusicStudio riconoscibile: usalo per i pacchetti e solo per quelli.

Il secondo segno è il **pentagramma**: cinque linee sottili con poche note. Si usa solo come decorazione, in testate e copertine, mai dietro un testo da leggere.

## Iconografia

- Icone a tratto, in una griglia di 24px, tratto da 2px (2.2–2.4 per le icone piccole), estremità arrotondate.
- Si disegnano inline con `stroke="currentColor"`, così prendono il colore del testo.
- Le icone usate sono: home, studenti (due persone), pagamenti (carta), esci, indietro, conferma (spunta), più, cerca, avviso.
- Il logo è una nota musicale doppia su un quadrato arancio con angoli `radius-sm`.

## Movimento

Movimenti brevi che spiegano da dove arriva una cosa, mai decorazione. Le durate sono i token `duration-fast` (120ms), `duration-base` (220ms) e `duration-slow` (320ms); le curve sono `ease-out-soft` per quasi tutto e `ease-bounce` solo per la battuta. Il dettaglio è nella sezione **Movimento**. Con "riduci movimento" attivo restano solo le dissolvenze.

## Accessibilità

- Testo almeno 4.5:1 sul suo fondo in entrambi i temi; ogni coppia di token lo rispetta e la nota del token dice su quali fondi.
- Elementi interattivi veri (`button`, `a`, `input` con `label`); i pulsanti con sola icona hanno un `aria-label`.
- Il focus da tastiera è un contorno di 2px in `orange-text`.
- Lo stato non si comunica solo col colore: ogni etichetta ha anche il suo testo.

## Usare il sistema

- **Token**: `tokens.json` è la fonte; il CSS compilato espone ogni token come variabile (`var(--paper)`, `var(--radius-card)`, `var(--duration-base)`) e cambia tema con `data-theme="light"` o `data-theme="dark"` sull'elemento `html`.
- **Kit CSS**: `components/bundle.css` contiene i componenti come classi con prefisso `ms-` (`ms-btn ms-btn--primary`, `ms-chip ms-chip--ok`, `ms-beats`). Funziona in qualsiasi progetto web che carichi anche i token.
- **App mobile**: React Native non legge il CSS. Si usano gli stessi valori di `tokens.json` in un file di tema TypeScript, con le stesse regole di questa guida.
- **Dati veri**: i moduli per creare e modificare studenti, pacchetti e lezioni usano `Dialog` sul web e `BottomSheet` su mobile, con i campi di `TextField`; il metodo di pagamento è un gruppo di pillole (`ms-radio-pill`). Vedi la scheda **FormFields**.
- Ogni componente ha la sua scheda con l'anteprima e le regole d'uso.

## Nel repository

Copia versionata del design system "MusicStudio" (claude.ai, 10 nov 2026); è la stessa del
branch `main` (`design/system/`). `tokens.json` è la fonte: `npm run tokens` genera
`src/constants/tokens.generated.ts`, che `src/constants/theme.ts` riesporta con i nomi usati
dall'app. Il kit CSS (`components.css`) vale solo per il web: qui i componenti sono in
`src/components/` e seguono le stesse regole.
