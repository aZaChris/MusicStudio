# FormFields

Moduli per inserire dati veri: nuovo studente, nuovo pacchetto, programma lezione, registra pagamento. Sul web stanno in `Dialog`, su mobile in `BottomSheet`.

- **Campi:** `TextField` con etichetta sempre visibile; bordo a riposo `field-border`, attivo `orange`, errore `bad-fg`.
- **Metodo di pagamento:** gruppo `fieldset.ms-fieldset` con `legend` e pillole `label.ms-radio-pill` (`data-checked="true"` sulla scelta): `ink` pieno, mai solo il colore.
- **Opzioni sì/no:** `label.ms-check`, bersaglio di almeno 44px.
- **Pulsanti:** Annulla (secondario) e azione (primario) a destra; azioni piccole nelle righe con `ms-btn--s`.
- **Date e orari:** l'utente scrive l'ora locale; l'app la converte in UTC per il server. Importi con la virgola decimale.
- **Errori:** il conflitto tra lezioni (409) si mostra nel modulo con `ms-alert--error`, dicendo cosa fare.
