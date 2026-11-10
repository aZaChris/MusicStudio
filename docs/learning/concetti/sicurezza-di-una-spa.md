# Sicurezza di una SPA: XSS, Content-Security-Policy e token nel browser

## TL;DR

Una SPA vive nel browser dell'utente, insieme a tutto quello che la pagina carica. Il rischio principale è l'XSS: uno script estraneo che gira nella pagina con gli stessi poteri del portale. Nel portale di MusicStudio lo limitiamo in tre modi: React che non interpreta l'HTML, una Content-Security-Policy che permette solo script del portale stesso, e una sessione in cui il token di accesso sta in memoria e il refresh token cambia a ogni uso. Il refresh token in `localStorage` resta un rischio accettato, scritto nero su bianco.

## Il problema reale

Il backend può essere perfetto, con permessi, scoping e test, ma se uno script estraneo gira nel portale, agisce **come l'utente**. Può leggere quello che l'utente vede, chiamare le API con i suoi token, e mandare i dati altrove.

Uno script estraneo può arrivare in vari modi: un dato del server mostrato come HTML, una libreria compromessa, uno snippet di analytics, un'estensione del browser. Il nome tecnico è **XSS** (Cross-Site Scripting).

Per MusicStudio la domanda concreta era: dove teniamo i token, e cosa può fare uno script se ci arriva?

## Come funziona

Pensa a un appartamento con una cassaforte. L'XSS è un estraneo che è già entrato in casa. La CSP è la regola del portiere: "entra solo chi è sulla lista". La cassaforte è il posto dove tieni le chiavi.

**Content-Security-Policy (CSP).** È un'intestazione HTTP che dice al browser da dove la pagina può caricare script, stili, immagini, e verso dove può connettersi. Con `script-src 'self'` il browser esegue solo i file JavaScript serviti dal portale stesso: uno script inline iniettato nella pagina viene bloccato. Con `connect-src 'self' https://api...` la pagina può chiamare solo il portale e le API, quindi uno script che riuscisse a girare non potrebbe mandare i dati a un server qualsiasi con `fetch`.

**Dove tenere i token.** Ci sono tre posti, con rischi diversi:

- **memoria** (una variabile JavaScript): sparisce ricaricando la pagina; uno script iniettato potrebbe comunque usarla mentre la pagina è aperta, ma non la trova salvata da nessuna parte;
- **`localStorage`**: resta tra una visita e l'altra; qualunque script della pagina lo legge;
- **cookie httpOnly**: JavaScript non lo può leggere affatto; il browser lo manda da solo, quindi serve una protezione contro le richieste forgiate (CSRF).

## Come lo abbiamo applicato in MusicStudio

**React non interpreta l'HTML.** Tutto quello che arriva dal server, come i nomi degli allievi o le note delle lezioni, React lo mostra come testo. Nel portale non c'è nessun `dangerouslySetInnerHTML`. È la prima difesa contro l'XSS, e la più importante.

**La CSP stretta.** È in `frontend/nginx/default.conf.template`:

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self';
  style-src 'self'; img-src 'self' data:; font-src 'self';
  connect-src 'self' ${API_ORIGIN}; object-src 'none'; base-uri 'self';
  form-action 'self'; frame-ancestors 'none'" always;
```

Niente `unsafe-inline` e niente `unsafe-eval`. Prima di sceglierla abbiamo controllato che l'`index.html` di produzione non contenga script o stili inline: Vite genera solo un `<script src>` e un `<link>`. Gli stili scritti in React con `style={{...}}` non sono un problema, perché React li imposta dal JavaScript del portale e non come attributi HTML. `frame-ancestors 'none'` impedisce a un altro sito di mostrare il portale in un iframe, per esempio per un attacco di clickjacking.

**I token.** Il token di accesso, che dura 15 minuti, sta solo in memoria. Il refresh token sta in `localStorage`, ed è un rischio accettato dal proprietario (ADR-023). Lo rendono più piccolo tre cose:

- la CSP rende difficile che uno script estraneo giri;
- il refresh token cambia a ogni rinnovo, e il vecchio non funziona più;
- il logout lo invalida sul server: la verifica end-to-end lo ha provato, il vecchio token ha ricevuto 401.

**Prima e dopo.** Prima il portale salvava **entrambi** i token in `localStorage` e non salvava il refresh token ruotato: gli utenti venivano disconnessi dopo circa 30 minuti. Ora il token di accesso non tocca mai lo storage, e un test lo controlla.

**Il CORS.** Le API accettano chiamate dal browser solo dall'origine del portale. Un sito estraneo che provi a chiamarle da un browser viene fermato dal browser stesso.

## Alternative considerate

**Refresh token in un cookie httpOnly.** È la soluzione migliore contro il furto del token via XSS, ed è il prossimo passo. Richiede però modifiche al backend: un endpoint che imposti il cookie, la protezione CSRF e il CORS con credenziali. Per questa fase il proprietario ha scelto di non toccare il backend.

**CSP con `unsafe-inline`.** Più comoda, ma toglie quasi tutta la protezione contro l'XSS.

**Nonce o hash per gli script inline.** Servono se ci sono script inline. Il portale non ne ha, quindi `'self'` basta ed è più semplice.

## Errori comuni e trade-off

- **Usare `dangerouslySetInnerHTML` con dati del server**: è il modo più rapido per creare un XSS in React.
- **Aggiungere `unsafe-inline` per far funzionare uno snippet**: meglio servire lo snippet come file.
- **Credere che la CSP basti.** È una seconda linea di difesa, non la prima.
- **Dimenticare `connect-src`.** Senza, uno script riuscito potrebbe mandare i dati ovunque.
- **Trade-off:** il refresh token in `localStorage` sopravvive alla chiusura del browser, comodo per l'utente, ma è leggibile da uno script. La rotazione e il logout lato server limitano il danno, non lo azzerano.

## Come lo spiegheresti a un colloquio

Nel portale il rischio principale è l'XSS, perché uno script estraneo agisce con i poteri dell'utente. La prima difesa è React, che mostra i dati come testo, e nel codice non c'è nessun `dangerouslySetInnerHTML`. La seconda è una Content-Security-Policy stretta, senza `unsafe-inline`: script solo dal portale, connessioni solo verso le API, niente iframe da altri siti. Il token di accesso sta in memoria; il refresh token sta in `localStorage`, ed è un rischio che ho documentato in un ADR insieme al passo successivo, un cookie httpOnly. La rotazione dei refresh token e il logout lato server limitano quanto vale un token rubato.

## Domande di autoverifica

1. **Cos'è l'XSS e perché è grave in una SPA?**
   È uno script estraneo che gira nella pagina. Agisce come l'utente: legge i dati e chiama le API con i suoi token.

2. **Cosa blocca `script-src 'self'`?**
   L'esecuzione di qualunque script che non sia un file servito dal portale stesso, compresi gli script inline iniettati.

3. **Perché il token di accesso non sta in `localStorage`?**
   Perché non serve salvarlo: dura 15 minuti e si rinnova con il refresh token. Tenerlo solo in memoria riduce quello che uno script trova.

4. **Perché il refresh token in `localStorage` è un rischio accettato e non risolto?**
   Perché la soluzione, un cookie httpOnly, richiede modifiche al backend. Il proprietario ha deciso di farle in una fase successiva; il rischio è documentato.

5. **A cosa serve `frame-ancestors 'none'`?**
   Impedisce ad altri siti di mostrare il portale in un iframe, per esempio per ingannare l'utente e fargli cliccare qualcosa senza saperlo.
