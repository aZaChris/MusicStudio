# Versionamento e deprecazione di un'API

## TL;DR

Un'API pubblica è una promessa: chi l'ha usata ieri deve poterla usare anche domani. Quando una modifica romperebbe i client, non la si fa di nascosto. La si annuncia con un preavviso, il comportamento vecchio resta vivo fino a una data, e solo dopo si toglie. In MusicStudio questo vuol dire una policy scritta con 90 giorni di preavviso, un decoratore che aggiunge i segnali standard a ogni risposta, un registro con un promemoria settimanale e un controllo in CI che blocca le modifiche incompatibili non dichiarate.

## Il problema reale

Il backend lo controlliamo noi: lo cambiamo, lo deployiamo, e in pochi minuti la versione nuova è online. I client no. L'app mobile sta sui telefoni delle famiglie e si aggiorna dagli store quando la persona lo decide, cioè a volte mai. Il portale web si aggiorna subito, ma ha i suoi tipi generati dal contratto.

Immagina di rinominare il campo `start_time` delle lezioni in `starts_at`, perché suona meglio. Il backend funziona, i test passano. Il giorno dopo l'app installata su un telefono legge `start_time`, non lo trova, e mostra una lezione senza orario, oppure si chiude. Nessun errore ci avvisa: il problema è sul telefono di qualcun altro.

Ci servono tre cose: sapere **cosa** rompe un client, **impedire** che una rottura passi per sbaglio, e quando una rottura è voluta, **dirlo per tempo** in un modo che qualcuno noti davvero.

## Come funziona, con un'analogia

Pensa a una linea di autobus che cambia percorso. L'azienda non sposta la fermata di notte senza dirlo a nessuno. Mette un cartello alla fermata vecchia: "dal 31 marzo questa fermata non sarà più servita, usate quella di via Roma". Lo scrive sul sito e sull'orario stampato. Per qualche mese l'autobus passa ancora da lì. Il 31 marzo la fermata chiude, e il cartello resta a dire dove andare.

Nell'API il cartello sono le intestazioni HTTP che ogni risposta porta:

- `Deprecation`: da quando l'endpoint è deprecato. L'RFC 9745 del 2025 lo scrive come una data strutturata, `@` seguito dai secondi dal 1970.
- `Sunset`: la data in cui verrà tolto (RFC 8594).
- `Link`: dove andare (`rel="successor-version"`) e dove leggere le regole (`rel="deprecation"`).

L'orario stampato è il contratto OpenAPI, dove l'operazione è segnata `deprecated: true`. Il sito è il registro delle deprecazioni. Dopo il 31 marzo la "fermata chiusa" è una risposta **410 Gone**: "qui c'era qualcosa, ed è stato tolto". Non un 404 generico, che sembrerebbe un errore di battitura.

## Come lo abbiamo applicato in MusicStudio

La policy sta in `docs/operations/api-versioning-policy.md`, in inglese, perché la leggono gli sviluppatori dei client. Dice che dentro `v1` si fanno solo modifiche compatibili: endpoint nuovi, campi nuovi nelle risposte, campi facoltativi nuovi nelle richieste. Tutto il resto rompe. Il preavviso minimo è di 90 giorni.

Il meccanismo è un decoratore di classe, in `apps/common/deprecation.py`:

```python
@deprecated(
    endpoint="GET /api/v1/things/",
    since=date(2026, 12, 1),
    sunset=date(2027, 3, 31),
    successor="/api/v2/things/",
    report="docs/operations/migrations/things.md",
)
class ThingsView(APIView): ...
```

Il decoratore crea una sottoclasse della view. In `finalize_response` aggiunge le tre intestazioni e scrive una riga di log `deprecated_call` con l'endpoint e l'intestazione `X-Client` (per esempio `mobile/1.4.2`), senza dati della persona. In `initial`, che DRF chiama prima del metodo vero, controlla la data: dopo il `sunset` solleva `EndpointGone`, che il gestore delle eccezioni trasforma in 410 con codice `endpoint_gone`. Con `extend_schema(deprecated=True)` lo segna anche nel contratto. Se il preavviso è più corto di 90 giorni, l'import fallisce: l'errore esce subito nei test e non arriva mai in produzione.

Il problema vero, però, è umano: le intestazioni le leggono le macchine, non le persone. Per questo ci sono altri due pezzi:

- **Il registro** `docs/operations/deprecations.md`, con un rapporto di migrazione per ogni deprecazione (modello in `migrations/TEMPLATE.md`). Un test confronta il registro con il codice: una deprecazione senza riga o senza rapporto fa fallire la CI.
- **Il promemoria con scadenza**: un workflow settimanale lancia il comando `deprecation_report`, che stampa i giorni rimasti e diventa rosso a 30 giorni dalla data. GitHub manda l'email del fallimento. Non gira sulle pull request, così una data del calendario non blocca lavoro che non c'entra.

Ultimo pezzo, la rete di sicurezza: il job di CI `contract-diff` confronta il contratto del branch con quello di `main` usando `oasdiff breaking`. Prima di attivarlo l'abbiamo provato davvero. Sul contratto prima e dopo la fase 9 le regole predefinite davano 13 errori, tutti falsi allarmi: valori aggiunti alla lista delle azioni di audit, e un cambio di forma `allOf` con gli stessi valori. Con `--flatten-allof` e un file che declassa "valore di enum aggiunto in risposta" ad avviso, gli errori sono 0. Rinominando `start_time` in una copia di prova, invece, gli errori sono 10 e il job fallisce.

## Alternative considerate

Creare subito un `/api/v2/`: niente è ancora incompatibile, sarebbe codice da mantenere senza motivo. Usare il versionamento di DRF (`NamespaceVersioning`): macchinario per una versione che non esiste. Mettere la data come test nella pipeline normale: il giorno X tutte le pull request diventerebbero rosse, anche quelle su altro. Scrivere da noi il confronto del contratto: è un progetto a sé, ed è facile sbagliarlo. Un `diff` di testo dice che il file è cambiato, non se il cambiamento è sicuro.

## Errori comuni e trade-off

- **Credere che basti l'intestazione.** Nessuno guarda le intestazioni finché qualcosa non si rompe. Servono anche un registro e un promemoria che arrivi a una persona.
- **Il 404 dopo la rimozione.** Sembra un URL sbagliato e fa perdere tempo. Il 410 dice esattamente cosa è successo.
- **Accettare ciecamente le regole di uno strumento.** oasdiff considera un errore anche un valore nuovo in un enum di risposta. Ha ragione in astratto: un client con uno `switch` senza ramo di default si rompe. Noi l'abbiamo declassato ad avviso, perché la lista delle azioni cresce per natura, e in cambio la policy chiede ai client di gestire i valori sconosciuti. È un compromesso, e va detto.
- **Contare le chiamate a occhio.** Il report scrive "unknown" finché i log non stanno in un archivio interrogabile. Inventare un numero sarebbe peggio.

## Come lo spiegheresti a un colloquio

Un'API che ha client che non controlli è un contratto, quindi le modifiche incompatibili non si fanno di nascosto. Abbiamo una policy con 90 giorni di preavviso, e un decoratore che aggiunge `Deprecation`, `Sunset` e `Link` secondo gli RFC, segna l'operazione come deprecata nel contratto e risponde 410 dopo la data. Siccome le intestazioni le leggono solo le macchine, c'è anche un registro controllato da un test e un workflow settimanale che diventa rosso a 30 giorni dalla rimozione. In CI, oasdiff confronta il contratto con quello di `main` e blocca le rotture non dichiarate; l'abbiamo tarato su una prova reale che dava 13 falsi allarmi. Un `v2` lo creeremo solo con la prima rottura vera, accanto al `v1`.

## Domande di autoverifica

1. **Perché un campo nuovo in una risposta è compatibile, e un campo nuovo obbligatorio in una richiesta no?**
   Un client vecchio ignora un campo che non conosce. Un client vecchio non manda un campo che non conosce, quindi un campo obbligatorio nuovo gli farebbe ricevere un 400.
2. **Che differenza c'è tra `Deprecation` e `Sunset`?**
   `Deprecation` dice da quando l'endpoint è sconsigliato. `Sunset` dice quando smetterà di funzionare. Nel mezzo c'è il preavviso.
3. **Perché il controllo della data non è un test nella CI normale?**
   Perché fallirebbe in base al calendario, rendendo rosse pull request che non c'entrano. Il workflow settimanale avvisa senza bloccare.
4. **Cosa risponde un endpoint dopo la data di rimozione, e perché non 404?**
   Risponde 410 con codice `endpoint_gone`: il client capisce che l'endpoint è stato tolto apposta e trova il link alla policy. Un 404 sembra un errore nell'URL.
5. **Qual è il prezzo della configurazione di oasdiff che abbiamo scelto?**
   I valori nuovi negli enum di risposta passano come avvisi: un client che non gestisce i valori sconosciuti potrebbe rompersi senza che la CI lo fermi. Lo copre la regola della policy che chiede ai client di gestirli.
