# L'IP reale del client dietro un proxy

## TL;DR

Dietro un reverse proxy il server non vede l'indirizzo del client, ma quello del proxy. L'indirizzo vero arriva nell'header `X-Forwarded-For`, che però in parte scrive il client. In MusicStudio una sola impostazione, `TRUSTED_PROXY_COUNT`, dice quanti proxy sono fidati, e l'IP si legge contando da destra. La usano l'allowlist del webhook di Stripe e i limiti di rate. Proprio qui abbiamo trovato un bug: il limite sui tentativi di login si poteva aggirare.

## Il problema reale

In produzione MusicStudio sta dietro Traefik, il proxy di Coolify. Traefik riceve la connessione HTTPS dal client e apre una nuova connessione verso gunicorn. Per gunicorn, quindi, ogni richiesta arriva dall'indirizzo di Traefik.

Ma in due punti ci serve l'IP vero. Il primo è il webhook di Stripe: vogliamo accettare solo gli indirizzi che Stripe pubblica. Il secondo è il rate limiting del login: cinque tentativi al minuto **per client**. Se tutti sembrano venire dallo stesso IP, il limite blocca tutti insieme. Se invece l'IP lo sceglie il client, il limite non blocca nessuno.

## Come funziona

Pensa a un pacco che passa per più corrieri. Ogni corriere, quando lo riceve, aggiunge sull'etichetta una riga: "ricevuto da...". L'ultimo corriere è il tuo, e di lui ti fidi. Ma le righe scritte prima che il pacco arrivasse al tuo corriere le può aver scritte chiunque, anche il mittente, che può inventarle.

`X-Forwarded-For` è quell'etichetta. È una lista di indirizzi separati da virgola, e ogni proxy **aggiunge in fondo** l'indirizzo da cui ha ricevuto la connessione. Per esempio:

```
X-Forwarded-For: 3.18.12.63, 6.6.6.6
```

Se davanti all'app c'è un solo proxy fidato, l'unico valore affidabile è l'ultimo, `6.6.6.6`: l'ha scritto Traefik, ed è l'indirizzo vero di chi si è collegato. Il primo, `3.18.12.63`, l'ha mandato il client. Potrebbe essere un attaccante che finge di essere Stripe.

La regola quindi è: **conta da destra quanti proxy fidati hai**, e prendi quel valore. Mai il primo da sinistra.

## Come lo abbiamo applicato in MusicStudio

**Una funzione.** `client_ip()` in `backend/apps/common/net.py`:

```python
def client_ip(request):
    trusted = settings.TRUSTED_PROXY_COUNT
    remote = str(request.META.get("REMOTE_ADDR", ""))
    if trusted <= 0:
        return remote
    forwarded = [p.strip() for p in request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")]
    forwarded = [p for p in forwarded if p]
    if len(forwarded) < trusted:
        return remote
    return forwarded[-trusted]
```

Con 0 proxy, in sviluppo, usa l'indirizzo della connessione. In produzione `TRUSTED_PROXY_COUNT` vale 1. Se un giorno si mette Cloudflare davanti a Coolify, diventa 2.

**L'allowlist di Stripe.** Il webhook controlla `client_ip()` contro `STRIPE_WEBHOOK_ALLOWED_IPS` prima di leggere il corpo. Fuori lista: 403, una riga di log, niente salvato. La firma resta obbligatoria comunque. Un test manda `X-Forwarded-For: <ip di Stripe>, 6.6.6.6` e verifica che venga rifiutato (ADR-021).

**Il bug del login.** Durante il giro OWASP ho riletto come DRF identifica il client nei throttle. La funzione `get_ident()` guarda l'impostazione `NUM_PROXIES`. Se non è definita, e non lo era, usa **tutta** l'intestazione `X-Forwarded-For`, tolti gli spazi, come identità. Quindi un attaccante poteva mandare un valore diverso a ogni tentativo, e ogni valore aveva il suo contatore, sempre a zero. Tentativi di password illimitati. E non serviva nemmeno un proxy: l'header lo può mandare chiunque.

Il vecchio test sul login passava, perché non mandava mai quell'header. La correzione è una riga, che lega DRF alla stessa impostazione di `client_ip()`:

```python
"NUM_PROXIES": TRUSTED_PROXY_COUNT,
```

Il nuovo test manda sei tentativi sbagliati, ognuno con un'origine falsa diversa, e si aspetta 429 al sesto. Ho anche verificato il prima: con `NUM_PROXIES` non definito, i sei tentativi davano tutti 401, cioè nessun limite.

## Alternative considerate

**Leggere il primo valore di `X-Forwarded-For`.** È quello che fanno molti esempi online, ed è proprio il valore che il client controlla.

**La libreria django-ipware.** Fa questo lavoro con molte opzioni, ma è una dipendenza per una funzione di dieci righe, e va comunque configurata con il numero di proxy giusto.

**Allowlist e limiti nel proxy.** Traefik può farlo, prima ancora di Django. Ma la configurazione starebbe fuori dal repository e fuori dai test.

**L'header `Forwarded` standard (RFC 7239).** Più strutturato, ma Traefik e quasi tutti gli strumenti usano ancora `X-Forwarded-For`.

## Errori comuni e trade-off

- **Fidarsi del primo valore.** È scritto dal client.
- **Fidarsi dei default delle librerie.** Il default di DRF va bene per un server senza proxy e senza attaccanti. Dietro un proxy va configurato.
- **Sbagliare il numero di proxy.** Troppo basso: si vede l'IP di un proxy, e tutti i client sembrano uno solo. Troppo alto: si torna a leggere un valore scritto dal client.
- **Due impostazioni per la stessa cosa.** Avevamo `TRUSTED_PROXY_COUNT` per noi e `NUM_PROXIES` per DRF, e solo la prima era impostata. Ora la seconda deriva dalla prima.
- **Trade-off:** se l'infrastruttura davanti all'API cambia, va cambiato anche il numero. Il runbook lo dice.

## Come lo spiegheresti a un colloquio

Dietro un reverse proxy il server vede l'IP del proxy, e quello del client arriva in `X-Forwarded-For`, dove ogni proxy aggiunge in fondo l'indirizzo da cui riceve la connessione. Quindi l'unico valore affidabile è quello aggiunto dal nostro proxy: si conta da destra quanti proxy fidati ci sono, e non si legge mai il primo valore, che scrive il client. In MusicStudio una sola impostazione, `TRUSTED_PROXY_COUNT`, guida sia la funzione che uso per l'allowlist di Stripe sia i throttle di DRF. Ho trovato che DRF, senza `NUM_PROXIES`, usava tutto l'header come identità, quindi il limite sul login si aggirava cambiando l'header a ogni tentativo. L'ho corretto e ho scritto un test che prova proprio l'attacco.

## Domande di autoverifica

1. **Perché dietro un proxy `REMOTE_ADDR` non basta?**
   Perché contiene l'indirizzo del proxy, non quello del client.

2. **Perché si conta da destra in `X-Forwarded-For`?**
   Perché ogni proxy aggiunge in fondo. Gli ultimi valori li scrivono i nostri proxy fidati, i primi li può scrivere il client.

3. **Come si aggirava il limite sui tentativi di login?**
   Mandando un `X-Forwarded-For` diverso a ogni tentativo: DRF senza `NUM_PROXIES` usava tutto l'header come identità, quindi ogni tentativo aveva un contatore nuovo.

4. **Cosa succede se `TRUSTED_PROXY_COUNT` è troppo alto?**
   Si legge un valore scritto dal client, che può così scegliere il suo IP, aggirando allowlist e limiti.

5. **Perché il controllo dell'IP sul webhook avviene prima della firma?**
   Per rifiutare subito chi non è Stripe, senza nemmeno leggere il corpo o calcolare l'HMAC.
