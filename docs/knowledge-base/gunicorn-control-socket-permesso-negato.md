# Gunicorn 26: "Control server error: Permission denied: '/.gunicorn'"

## Sintomo

Nel log del `backend` su Coolify, a ogni avvio, subito dopo "Booting worker":

```
[ERROR] Control server error: [Errno 13] Permission denied: '/.gunicorn'
```

Il backend era comunque sano: i worker partivano e `/health/ready/` rispondeva 200.

## Causa radice

Da gunicorn 25.1 il processo principale apre un "control socket" (un file Unix) per lo strumento
`gunicornc`, che permette di vedere i worker e cambiarne il numero a runtime. Se non è
impostato `XDG_RUNTIME_DIR`, il file va in `$HOME/.gunicorn/gunicorn.ctl`.

Il nostro container gira come utente numerico `10001`, senza una home scrivibile: `HOME` vale `/`,
quindi gunicorn prova a creare `/.gunicorn` e riceve `Permission denied`. L'errore non ferma il
server: perde solo l'interfaccia di controllo, che non usiamo.

## Come l'abbiamo confermata

Con l'ambiente virtuale del progetto, avviando gunicorn con `HOME=/nonexistent` (non
scrivibile): senza opzioni compare lo stesso errore, con `--no-control-socket` sparisce e il resto
dell'avvio è identico. (Con `uv run` la prova non è valida: `uv` usa `HOME` per la sua cache.)

## Risoluzione

`--no-control-socket` nel comando gunicorn di `backend/docker/entrypoint.sh`. Abbiamo scelto di
spegnere il socket invece di dargli una home scrivibile: non usiamo `gunicornc`, e un'interfaccia
di controllo in meno è meno superficie da proteggere.

## Lezione per il futuro

Un aggiornamento di una libreria può aggiungere una funzione che scrive su disco. Un container non
root senza home la scopre al primo avvio, come errore nel log. Un errore che non ferma il servizio
si ignora facilmente: meglio capirlo, perché rumore nei log nasconde gli errori veri. Quando
una dipendenza aggiunge un'interfaccia che non usiamo, la disattiviamo.

## Riferimenti

- `backend/docker/entrypoint.sh`
- Impostazioni gunicorn `control_socket` e `--no-control-socket` (disponibili da 25.1)
