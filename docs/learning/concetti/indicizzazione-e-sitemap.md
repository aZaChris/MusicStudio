# Indicizzazione, sitemap e robots.txt di una SPA

## TL;DR

Un sito si fa trovare da Google solo se gli si dice cosa è, dove sono le sue pagine e se può comparire nei risultati. Sono quattro cose: i metadati nella pagina, `robots.txt`, la sitemap e un'intestazione che apre o chiude l'indicizzazione. In MusicStudio il sito resta chiuso per impostazione predefinita, e si apre a mano solo in produzione. Una SPA ha una trappola in più: il fallback delle rotte può far sembrare un file inesistente una pagina HTML.

## Il problema reale

Il 13 novembre 2026 il proprietario ha lanciato Lighthouse sullo staging, prima di aprire il sito a Google. Il risultato:

- «Il documento non ha una meta descrizione»;
- «robots.txt non è valido, 16 errori trovati»;
- «Il documento ha un elemento `rel=canonical` valido»: non applicabile, perché non c'era.

La prima voce era vera: `index.html` aveva solo il `<title>`. La seconda sembrava strana, perché non avevamo un `robots.txt`. La causa era il fallback della SPA (vedi il concetto sul deploy con nginx): per ogni indirizzo che non è un file, nginx risponde con `index.html`. Chiedendo `/robots.txt` si riceveva una pagina HTML, e Lighthouse provava a leggerla come regole. Ogni riga di HTML era un errore.

Lo abbiamo confermato con `curl`: sullo staging `/robots.txt` rispondeva con `<!doctype html>`.

## Come funziona

Pensa a un palazzo con un portiere e una guida turistica.

- **I metadati** sono la targhetta all'ingresso: nome e descrizione in una riga. Google la mostra sotto il titolo nei risultati.
- **`robots.txt`** è il cartello del portiere: «gli ospiti possono entrare» oppure «chiuso». Sta sempre allo stesso indirizzo.
- **La sitemap** è la piantina delle stanze visitabili: un elenco di indirizzi, uno per riga.
- **`noindex`** è un biglietto diverso: «puoi entrare, ma non mettermi nella guida». Si manda con un'intestazione HTTP, `X-Robots-Tag`.
- **Il link canonico** dice qual è l'indirizzo ufficiale quando la stessa pagina si raggiunge da più strade.

La regola da ricordare: il cartello e il biglietto si contraddicono. Se `robots.txt` vieta l'ingresso, il crawler non apre la pagina e non vede mai il `noindex`.

## Come lo abbiamo applicato in MusicStudio

**1. Metadati.** `frontend/index.html` ha ora descrizione, tag Open Graph (l'anteprima quando condividi il link) e la lingua della pagina, che segue la lingua scelta nell'app. Il canonical e l'immagine di anteprima hanno bisogno dell'indirizzo assoluto del sito, che sa solo la build (`VITE_SITE_URL`). Li aggiunge un piccolo plugin di Vite, solo se l'indirizzo c'è:

```ts
const PUBLIC_PAGES = ['/', '/register']

generateBundle() {
  const robots = ['User-agent: *', 'Allow: /']
  if (site) {
    this.emitFile({ type: 'asset', fileName: 'sitemap.xml', source: sitemapXml(site) })
    robots.push('', `Sitemap: ${site}/sitemap.xml`)
  }
  this.emitFile({ type: 'asset', fileName: 'robots.txt', source: robots.join('\n') + '\n' })
}
```

**2. Chiuso per impostazione predefinita.** Il container del sito manda `X-Robots-Tag` con il valore della variabile `ROBOTS_TAG`, che nell'immagine vale `noindex, nofollow`. La produzione la apre a mano con `index, follow`. Se ti dimentichi, il sito resta nascosto invece di comparire per errore.

```nginx
add_header X-Robots-Tag "${ROBOTS_TAG}" always;
```

**3. L'API non si indicizza mai.** Un middleware aggiunge `X-Robots-Tag: noindex, nofollow` a ogni risposta del backend, file statici e 404 compresi. Non ha interruttore, perché non esiste un ambiente in cui l'API debba comparire nelle ricerche.

**4. La sitemap elenca solo quello che un visitatore già vede.** Due pagine: `/` e `/register`. Niente accesso, aree private, indirizzi dell'API o file multimediali: il video del marchio non è nominato né nella sitemap né nei metadati.

Prima e dopo, `curl https://…/robots.txt`:

```
prima:  <!doctype html> <html lang="en"> …
dopo:   User-agent: *
        Allow: /
        Sitemap: https://…/sitemap.xml
```

**Un difetto trovato provando.** Se `VITE_SITE_URL` è vuota (nel compose di Coolify lo è, finché non imposti `FRONTEND_URL`), un `<link rel="canonical" href="/">` nell'HTML faceva fallire la build: Vite provava a leggere `/` come file e dava `EISDIR`. La CI, che costruiva con un indirizzo valorizzato, non l'avrebbe mai visto. Ci siamo accorti costruendo il sito nei due modi. Per questo i tag li aggiunge il plugin solo quando l'indirizzo è noto.

**Un commento sbagliato.** Nel file nginx c'era scritto che l'HSTS lo imposta il proxy di Coolify. Con `curl -I` sullo staging non c'era. Ora lo imposta nginx.

## Alternative considerate

- **`Disallow: /` su staging**: scartata. Impedisce ai crawler di vedere il `noindex`, e se qualcuno linka lo staging l'indirizzo può comparire lo stesso, senza descrizione.
- **Un `robots.txt` diverso per ambiente**: scartata. Un'intestazione si cambia con una variabile, senza ricostruire l'immagine.
- **Rendering lato server (Next.js)**: rimandata. Con una sola pagina pubblica non cambia molto. Ricomincia a valere se arrivano più pagine di contenuto.
- **Sitemap scritta a mano**: scartata. Gli indirizzi cambiano per ambiente.

## Errori comuni e trade-off

- Dimenticare il `noindex` su staging e trovarsi lo staging su Google.
- Mettere nella sitemap pagine private o che reindirizzano al login.
- Canonical relativo o assente: Google sceglie lui l'indirizzo.
- **Trade-off:** `ROBOTS_TAG` chiuso di default significa che un deploy di produzione dove ci si dimentica di aprirlo resta invisibile. È voluto: è più facile accorgersene (nessuna visita da Google) che rimediare a una pagina indicizzata per errore.
- **Aspettative:** un sito nuovo, con un nome generico e su un sottodominio, non compare in cima a una ricerca per il solo nome. Indicizzare è il minimo. Poi servono pagine con testo vero e qualcuno che le linki.

## Come lo spiegheresti a un colloquio

Un sito si fa trovare con quattro strumenti: metadati, `robots.txt`, sitemap e l'intestazione `X-Robots-Tag`. In una SPA `robots.txt` può sembrare una pagina HTML perché il fallback risponde a tutto, e Lighthouse lo segnala. Da noi i file li genera la build e l'indicizzazione è chiusa per impostazione predefinita, così lo staging non finisce su Google per errore. La produzione la apre con una variabile. Un `Disallow` sarebbe stato peggio, perché nasconde il `noindex` ai crawler.

## Domande di autoverifica

1. **Perché `/robots.txt` dava «16 errori» su una SPA?**
   Il fallback delle rotte risponde con `index.html` a ogni indirizzo che non è un file. Lighthouse leggeva l'HTML come se fossero regole.

2. **Perché non mettere `Disallow: /` sullo staging?**
   Il crawler non aprirebbe le pagine e non vedrebbe mai il `noindex`. Il modo giusto è consentire la lettura e mandare `X-Robots-Tag: noindex`.

3. **Perché `noindex` è il valore predefinito e non quello da impostare?**
   Perché sbagliare in un verso costa poco (un sito invisibile per qualche giorno) e nell'altro costa molto (una pagina indicizzata che non doveva esserci).

4. **Perché il canonical lo aggiunge un plugin e non sta in `index.html`?**
   Perché ha bisogno dell'indirizzo assoluto, che sa solo la build. Un tag vuoto o relativo, in Vite, può far fallire la build.

5. **Cosa c'è nella sitemap e cosa no?**
   Solo `/` e `/register`. Niente accesso, aree private, API o file multimediali come il video.
