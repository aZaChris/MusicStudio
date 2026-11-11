# ADR-027: Principi di sicurezza e privacy per i dati dei minori

- Stato: accettato
- Data: 2026-11-11

## Contesto

MusicStudio contiene dati di bambini e ragazzi (nomi, strumento, lezioni, note dell'insegnante) e dati di pagamento delle loro famiglie. Fino alla fase 4 la sicurezza era trattata soprattutto come sicurezza delle API: isolamento tra studi, token, rate limiting, giro OWASP a fine fase.

Mancavano invece le regole sulla **privacy**: quali dati raccogliamo, chi può avere un account, come una famiglia esporta o cancella i suoi dati, per quanto tempo li teniamo, cosa finisce nei log. Senza un principio scritto, queste scelte si fanno caso per caso e si dimenticano.

Prima di andare in staging con persone vere, il proprietario ha aperto la fase 7, dedicata a sicurezza, privacy e account.

## Decisione

- La constitution passa alla versione **3.1.0** con il principio **X. Privacy by design per i dati dei minori**. Il principio vale per ogni fase futura, non solo per questa.
- Il principio fissa: minimizzazione dei dati (niente data di nascita, telefono o indirizzo); i minori entrano solo attraverso un genitore che dà un consenso registrato; export e cancellazione disponibili dal prodotto; testo libero sugli allievi cifrato; audit delle azioni delicate; niente dati personali nei log; segreti mai nella history di git; nessun modo di scoprire se un'email è registrata.
- **L'export GDPR si sposta dalla fase 5 alla fase 7**, perché senza export e cancellazione non si possono accogliere famiglie vere.
- **Le password restano con PBKDF2-SHA256**, l'algoritmo predefinito di Django 5.2 (un milione di iterazioni). È tra quelli raccomandati da OWASP. Il passaggio ad **Argon2id** è il miglioramento previsto se un giorno servirà: richiede la dipendenza `argon2-cffi` e Django sa aggiornare gli hash al primo login.

## Alternative scartate

- **Nessun principio, solo i task della fase**: le regole sparirebbero alla fase successiva. Il principio invece fa da cancello in ogni piano (`plan-template.md`, gate X).
- **Data di nascita per sapere se un allievo è minorenne**: è un dato in più, e cambia valore ogni giorno. Un'indicazione "maggiorenne sì/no" impostata dall'insegnante basta per decidere chi può avere un account.
- **Argon2id subito**: guadagno piccolo a questa scala, e una dipendenza in più. Il login è già il punto più lento nel load test della fase 4.

## Conseguenze

- Ogni piano futuro deve passare il gate X: per esempio i progressi e il materiale della fase 8 nasceranno con le note cifrate.
- I testi legali (registro dei trattamenti, informativa) sono **bozze**: vanno validati da un professionista prima di usare il prodotto con famiglie vere. È un compito del proprietario.
- La fase 7 è la più grande finora. Le storie sono indipendenti, quindi se il tempo manca slittano le meno urgenti, mai i test sull'isolamento.
