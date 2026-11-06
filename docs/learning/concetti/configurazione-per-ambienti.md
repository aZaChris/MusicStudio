# Configurazione per ambienti

## TL;DR

Lo stesso codice gira in sviluppo, nei test e in produzione, ma con impostazioni diverse. La regola dei "12 fattori" dice di tenere la configurazione nelle variabili d'ambiente, non nel codice. In MusicStudio abbiamo quattro moduli di settings (`base`, `dev`, `test`, `prod`). La produzione rifiuta di partire se manca un segreto e sa di stare dietro il proxy TLS di Coolify.

## Il problema reale

Un'applicazione Django ha decine di impostazioni. Alcune sono uguali ovunque, come le app installate. Altre cambiano: l'indirizzo del database, la chiave segreta, se mostrare gli errori dettagliati, quali domini accettare.

Se metti questi valori nel codice, succedono brutte cose. La chiave segreta finisce su GitHub. Per cambiare database devi fare un nuovo deploy. E prima o poi qualcuno va in produzione con `DEBUG = True`, che mostra a chiunque lo stack trace con i dettagli interni.

C'è anche un problema più sottile: le impostazioni sbagliate che non si vedono subito. Se manca la password SMTP, l'applicazione parte lo stesso e fallisce solo quando prova a mandare la prima email, magari alle tre di notte.

## Come funziona

Pensa a un attore che recita la stessa parte in teatri diversi. Il copione, cioè il codice, è sempre lo stesso. Cambiano il palco, le luci, il pubblico, cioè la configurazione. L'attore non riscrive il copione per ogni teatro: legge le indicazioni del teatro in cui si trova.

La metodologia "Twelve-Factor App" dice che la configurazione, cioè tutto quello che cambia tra un deploy e l'altro, deve stare nelle variabili d'ambiente. Il codice legge le variabili all'avvio. Lo stesso container può andare in staging o in produzione cambiando solo l'ambiente.

In Django un modo comune è avere un modulo di settings per ambiente. Tutti importano un modulo base, e ognuno sovrascrive quello che gli serve. La variabile `DJANGO_SETTINGS_MODULE` dice quale usare.

Due concetti importanti per la produzione.

**Fail fast.** Se manca un valore obbligatorio, l'applicazione deve rifiutarsi di partire, con un messaggio chiaro. Meglio un deploy fallito subito che un errore misterioso dopo ore.

**Il proxy TLS.** In produzione l'HTTPS non arriva fino a Django. Il proxy di Coolify riceve la connessione cifrata, la decifra e inoltra a gunicorn una richiesta HTTP normale, con un'intestazione `X-Forwarded-Proto: https`. Se Django non si fida di quell'intestazione, pensa che ogni richiesta sia in chiaro. Con il redirect HTTPS attivo, rimanda il client a HTTPS. Il client torna, il proxy inoltra di nuovo in HTTP, e così via: un loop infinito.

## Come lo abbiamo applicato in MusicStudio

I file sono in `backend/config/settings/`.

`base.py` legge tutto con django-environ: database, Redis, cache, limiti di frequenza, durata dei token, CORS, path dell'admin, livello di log. Ogni variabile è documentata in `.env.example` nella radice del repository.

`dev.py` attiva `DEBUG` e accetta qualsiasi host. Comodo in locale.

`test.py` è nuovo. Imposta una chiave fittizia, un hasher delle password veloce (MD5, accettabile solo perché le password dei test sono finte), cache ed email in memoria. Così i test non dipendono da Redis né dai segreti di chi li esegue.

`prod.py` è la parte più importante:

```python
SECRET_KEY = env("DJANGO_SECRET_KEY")          # nessun default: se manca, non parte
JWT_SIGNING_KEY = env("JWT_SIGNING_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_REDIRECT_EXEMPT = [r"^health/"]
```

L'eccezione per `/health/` serve perché i controlli di salute arrivano in HTTP dalla rete interna del container. Senza l'eccezione riceverebbero un redirect e il container risulterebbe non sano.

**Un bug trovato.** `config/wsgi.py` e `config/asgi.py` usavano come default `config.settings`, che è un package con un `__init__.py` vuoto. Se la variabile mancava, gunicorn partiva senza impostazioni. Funzionava solo perché il vecchio `.env` la impostava. Celery, invece, usava come default le impostazioni di sviluppo. Ora i tre entrypoint di produzione usano `config.settings.prod`.

**Le verifiche.** `backend/config/tests/test_settings.py` carica le impostazioni di produzione in un processo Python separato. Controlla che con tutte le variabili partano, e che senza `JWT_SIGNING_KEY` falliscano con il nome della variabile nell'errore. Ho anche avviato gunicorn con le impostazioni di produzione: richiesta in HTTP, redirect 301; richiesta con `X-Forwarded-Proto: https`, risposta normale; host sconosciuto, 400; intestazioni HSTS presenti.

## Alternative considerate

**Un solo file di settings con tanti `if DEBUG`.** Meno file, ma più difficile da leggere e più facile da sbagliare.

**pydantic-settings.** Validazione tipizzata delle variabili, molto elegante. Ma è una dipendenza in più per un problema che django-environ già risolve bene.

**Segreti con valori di default "comodi" anche in produzione.** Tipo `SECRET_KEY = env("...", default="changeme")`. Se qualcuno dimentica di impostarla, la produzione gira con una chiave nota a tutti. Inaccettabile.

## Errori comuni e trade-off

- **Committare il file `.env`.** Si committa solo `.env.example`, con valori finti.
- **Dimenticare `CSRF_TRUSTED_ORIGINS`.** Dietro HTTPS il login dell'admin fallisce con un errore CSRF.
- **`ALLOWED_HOSTS = ["*"]` in produzione.** Apre la porta agli attacchi sull'intestazione Host.
- **Trade-off nel build Docker:** `collectstatic` carica le impostazioni di produzione, che senza variabili non partono. Nel Dockerfile passiamo valori fittizi solo per quel comando. Funziona, ma è un punto da capire bene leggendo il file.
- **Trade-off sugli host:** in produzione aggiungiamo `localhost` agli host ammessi, per i controlli di salute interni al container. È sicuro perché il proxy inoltra solo il dominio configurato, ma va saputo.

## Come lo spiegheresti a un colloquio

Seguo i Twelve-Factor: tutta la configurazione che cambia tra ambienti arriva da variabili d'ambiente, documentate in un `.env.example`. Ho quattro moduli di settings: base, sviluppo, test e produzione. In produzione i segreti non hanno default, quindi se ne manca uno l'applicazione non parte e l'errore dice quale. Siccome Coolify termina il TLS al proxy, Django si fida dell'intestazione `X-Forwarded-Proto`, altrimenti il redirect HTTPS andrebbe in loop. Un test carica le impostazioni di produzione in un processo separato e verifica sia l'avvio corretto sia il fallimento senza segreti.

## Domande di autoverifica

1. **Perché i segreti di produzione non hanno valori di default?**
   Perché un default renderebbe possibile partire con un valore noto. Senza default, una variabile mancante blocca subito l'avvio.

2. **Cosa succede senza `SECURE_PROXY_SSL_HEADER` dietro il proxy di Coolify?**
   Django vede ogni richiesta come HTTP e, con il redirect attivo, rimanda sempre a HTTPS: un loop di redirect.

3. **Perché `/health/` è escluso dal redirect HTTPS?**
   Perché i controlli di salute arrivano in HTTP dalla rete interna. Con un redirect, il controllo fallirebbe.

4. **A cosa serve un modulo di settings separato per i test?**
   A rendere i test veloci e indipendenti: niente Redis, niente segreti reali, hasher veloce, email in memoria.

5. **Quale bug c'era negli entrypoint wsgi e asgi?**
   Puntavano a un package di settings vuoto. Funzionavano solo perché una variabile d'ambiente lo correggeva dall'esterno.
