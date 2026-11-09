# ADR-021: Allowlist degli IP di Stripe e IP reale dietro il proxy

- Stato: accettato
- Data: 2026-11-09

## Contesto

Il webhook di Stripe è un endpoint pubblico, senza login. Dalla fase 3 accetta solo eventi con una firma valida, calcolata con un segreto condiviso (ADR-014). Stripe pubblica anche la lista degli indirizzi IP da cui partono i suoi webhook e consiglia di usarla come secondo controllo. Era il punto aperto di OWASP API10.

Per controllare l'IP, però, serve sapere qual è l'IP vero. In produzione l'API sta dietro il proxy di Coolify (Traefik). Gunicorn vede solo l'indirizzo del proxy. L'indirizzo del client arriva nell'header `X-Forwarded-For`, che è una lista: ogni proxy **aggiunge in fondo** l'indirizzo da cui ha ricevuto la connessione. Tutto quello che sta a sinistra l'ha scritto il client, e il client può scrivere quello che vuole.

## Decisione

- Una funzione, `client_ip()` in `apps/common/net.py`, calcola l'IP reale. Con `TRUSTED_PROXY_COUNT = N` prende l'N-esimo valore **da destra** di `X-Forwarded-For`. Con 0 usa l'indirizzo della connessione. In produzione N vale 1 (solo Traefik); con Cloudflare davanti diventerebbe 2.
- La variabile `STRIPE_WEBHOOK_ALLOWED_IPS` contiene la lista degli IP di Stripe. Accetta anche intervalli CIDR.
- Il webhook controlla l'IP **prima** di leggere il corpo e la firma. Una richiesta da fuori lista riceve 403, viene registrata nei log e non viene salvata.
- Con la lista vuota il controllo è spento. Serve in sviluppo, nei test, e come via d'uscita temporanea se Stripe cambia indirizzi. La firma resta comunque obbligatoria.

## Alternative scartate

- **Leggere il primo valore di `X-Forwarded-For`**: è proprio quello che il client controlla. Un attaccante manderebbe `X-Forwarded-For: <ip di Stripe>` e passerebbe. Un test lo verifica.
- **Allowlist nelle regole di Traefik o di Coolify**: funzionerebbe, ma starebbe fuori dal repository e fuori dai test.
- **La libreria django-ipware**: una dipendenza per una funzione di dieci righe.
- **Solo la firma**: già sicura da sola, finché il segreto non viene esposto. L'allowlist è difesa in profondità sul percorso del denaro.

## Conseguenze

- Se Stripe aggiunge indirizzi e la lista non viene aggiornata, i webhook da quegli indirizzi ricevono 403. Stripe riprova per tre giorni, e la riconciliazione oraria (ADR-014) recupera i pagamenti persi nel frattempo. Il runbook dice dove prendere la lista aggiornata.
- Se `TRUSTED_PROXY_COUNT` è sbagliato, l'IP calcolato è sbagliato: con un valore troppo basso si vede l'IP del proxy e tutto viene rifiutato; con uno troppo alto il client torna a poter scegliere il suo IP. Il valore va cambiato solo se cambia l'infrastruttura davanti all'API.
- `client_ip()` è riutilizzabile ovunque serva l'IP del client, per esempio nei log o nel rate limiting.
