# `robots.txt` non valido: la SPA rispondeva con la pagina HTML

## Sintomo

Lighthouse sullo staging, sezione SEO: «robots.txt non è valido, 16 errori trovati». Nello stesso
controllo: «Il documento non ha una meta descrizione». Il progetto non aveva nessun `robots.txt`.

## Causa radice

Il sito è una SPA servita da nginx. Per ogni indirizzo che non è un file esistente, la
configurazione fa un fallback a `index.html` (serve alle rotte del client, come `/students`).
Anche `/robots.txt` non era un file, quindi rispondeva con `index.html`. Lighthouse leggeva quel
codice HTML come regole di `robots.txt`: ogni riga era un errore.

## Come l'abbiamo confermata

`curl https://<staging>/robots.txt` restituiva `<!doctype html> <html lang="en"> …` con stato 200
e tipo `text/html`. Lo stesso valeva per qualunque altro file inesistente.

## Risoluzione

La build genera un vero `robots.txt` (con `Allow: /`, e la riga `Sitemap:` quando si conosce
l'indirizzo del sito) e una `sitemap.xml`. Il file statico di prova è stato tolto, così non ci
sono due fonti. Nel job `web-image` della CI si controlla il contenuto dei due file.

## Lezione per il futuro

Con un fallback delle rotte, un file che «non esiste» non dà 404: dà la pagina iniziale. Vale per
`robots.txt`, `sitemap.xml`, `favicon` e `.well-known/`. Quello che un crawler si aspetta in un
indirizzo fisso va generato davvero e controllato in CI. Una risposta 200 non prova che il file
sia quello giusto: si guarda anche il tipo di contenuto.

## Riferimenti

- `frontend/vite.config.ts` (plugin `site-meta`), `frontend/nginx/default.conf.template`
- `docs/learning/concetti/indicizzazione-e-sitemap.md`, `docs/learning/concetti/deploy-di-una-spa-con-nginx.md`
