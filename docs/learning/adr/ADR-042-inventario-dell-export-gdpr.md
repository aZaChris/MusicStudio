# ADR-042: Un inventario di tutti i modelli rende l'export GDPR verificabile

- Stato: accettato
- Data: 2026-11-25

## Contesto

L'export dei dati personali è nato nella fase 7 (ADR-032). Le fasi 8 e 9 hanno aggiunto ricevute, storni, checkout online e conti collegati, ma nessuno ha aggiornato l'export, perché niente lo obbligava. Un export che dimentica dati in silenzio è un difetto di conformità (articoli 15 e 20 del GDPR), e "lo controlleremo" non è una garanzia.

## Decisione

- **`apps/privacy/inventory.py`**: un dizionario con **ogni** modello di `apps.*` (non solo quelli "personali"), associato a `("exported", "<chiave dell'export>")` oppure a `("excluded", "<motivo>")`.
- **Due test**: il primo elenca `apps.get_models()` e fallisce indicando per nome il modello che manca. Il secondo costruisce una famiglia completa e un titolare, e verifica che ogni chiave "exported" esista davvero nell'export. Così l'inventario non può mentire.
- **Analisi dei buchi fatta sul codice**, non a memoria. Ne sono usciti sette: stato della MFA (sì/no), numero della ricevuta su ogni pagamento, collegamento `reversal_of` degli storni, checkout online, promemoria inviati, inviti rivolti all'indirizzo della persona, e le voci del registro di cui la persona è l'autore. Sono stati aggiunti tutti come **chiavi nuove**: nessuna chiave esistente è cambiata, quindi i client non si rompono.
- **Esclusi con un motivo**: i segreti MFA e gli hash dei codici di recupero (sono credenziali), il record dell'insegnante (sono dati suoi, non della famiglia), le contestazioni (compaiono già come righe di storno, ADR-038), gli eventi di Stripe (già ripuliti, ADR-039). Gli inviti mandati **ad altri** non si esportano: contengono email di altre persone.
- **Export sincrono**, deciso con una misura. Il caso più grande realistico (1 genitore, 3 figli, 2 anni di lezioni settimanali: 312 lezioni, 78 pagamenti con ricevuta, 85 KB) richiede tra **47 e 167 ms**, contro un limite di 10 secondi.

## Alternative scartate

- **Riconoscere i dati personali dai nomi dei campi o dalle chiavi esterne verso `User`**: non vede i dati indiretti, come il pagamento di un figlio, e dà una falsa sicurezza.
- **Un attributo su ogni modello**: sparge la risposta in tanti file ed è facile da dimenticare.
- **Un export in background (Celery con link a scadenza)**: costruirlo senza una misura che lo richieda sarebbe YAGNI. Resta come `FUTURO (export in background)` in `apps/privacy/selectors.py`.

## Conseguenze

- Chi aggiunge un modello deve rispondere una volta, in review, alla domanda "va nell'export?". La CI lo costringe a farlo.
- L'export fa qualche query in più: una per tabella, mai una per figlio. Il budget del test è passato da 10 a 15 query, e un test con due figli prova che non cresce.
- Dopo una cancellazione l'export risponde comunque, e ogni figlio porta `anonymised_at`: dice cosa è rimasto e perché.
