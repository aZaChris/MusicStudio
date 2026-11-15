"""Modelli dei pagamenti: pagamento registrato, tentativo di checkout, evento webhook.

Per studiare: docs/learning/concetti/pagamenti-online-stripe.md (visione d'insieme),
ADR-013 (perché Stripe Checkout) e ADR-014 (perché i webhook si salvano prima di elaborarli).

FUTURO (pagamenti dentro l'app): oggi l'app non muove soldi veri, registra e basta. Se un
giorno si vorrà far pagare dall'app (PostePay, PayPal, carte) serviranno: un nuovo ADR che
sostituisca ADR-013 (oggi una chiave `sk_live_` blocca l'avvio, vedi config/settings/prod.py),
la scelta di chi incassa (Stripe Connect per ogni insegnante/studio, oppure un conto unico con
obblighi fiscali e legali) e un campo su questi modelli per distinguere il fornitore.
"""

import uuid

from django.conf import settings
from django.db import models

from apps.common.fields import EncryptedTextField
from apps.packages.models import Package
from apps.students.models import Student


class Payment(models.Model):
    """Un pagamento registrato: a mano dall'insegnante oppure creato dal webhook online.

    Sia i pagamenti manuali sia quelli online finiscono in questa tabella, così lo storico
    di uno studente è uno solo.
    """

    class Method(models.TextChoices):
        # Come è stato pagato. Descrive un pagamento GIÀ avvenuto: non dice quali metodi
        # l'insegnante accetta.
        CASH = "cash", "Cash"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"
        MANUAL_ENTRY = "manual_entry", "Manual entry"
        CARD = "card", "Online (Stripe)"
        # FUTURO (metodi di pagamento accettati): per far dichiarare a insegnanti e studi
        # IBAN, PayPal, Satispay o "contanti a fine lezione" serve un modello a parte,
        # per esempio `PaymentInstruction` legato allo studio, in sola lettura per i
        # genitori. L'IBAN è un dato personale: va cifrato come le note
        # (docs/learning/concetti/cifratura-dei-campi.md, ADR-030).

    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        PENDING = "pending", "Pending"
        OVERDUE = "overdue", "Overdue"
        # Riga di storno (fase 8): annulla un pagamento pagato senza riscriverlo. Vedi
        # `reversal_of` e specs/008-cash-register-receipts/data-model.md.
        REVERSAL = "reversal", "Reversal"

    # Lo studente cancellato porta con sé i suoi pagamenti (CASCADE). La cancellazione GDPR
    # però è un'anonimizzazione, non un delete: vedi ADR-032 e apps/privacy.
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="payments")
    # Se il pacchetto sparisce il pagamento resta (SET_NULL): è una traccia contabile.
    package = models.ForeignKey(
        Package, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    date = models.DateField()
    method = models.CharField(max_length=20, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    # Valorizzato solo per i pagamenti online. OneToOne = al massimo un pagamento per
    # tentativo di checkout, garantito dal database anche se un webhook arriva due volte
    # (ADR-014).
    checkout = models.OneToOneField(
        "payments.CheckoutSession",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payment",
    )
    # Solo sulla riga di storno: punta al pagamento originale. OneToOne = al massimo uno storno
    # per pagamento, garantito dal database anche con due richieste insieme (FR-004, FR-009).
    # CASCADE e non PROTECT: il job di conservazione cancella i pagamenti vecchi in blocco, e uno
    # storno recente di un pagamento molto vecchio non deve bloccarlo.
    reversal_of = models.OneToOneField(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="reversal"
    )
    # Perché si è stornato: testo libero, quindi cifrato (constitution X). Al massimo 200 caratteri,
    # controllati dal serializer.
    reason = EncryptedTextField(blank=True)
    # Chi ha creato la riga. Null per le righe vecchie e per il pagamento online (webhook).
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [
            # Ultimo pagamento di uno studente (sottoquery dell'elenco) e storico dello
            # studente. Perché gli indici: docs/learning/concetti/indici-ed-explain.md.
            models.Index(fields=["student", "-date"], name="payment_student_date_idx"),
            # Conteggio dei pagamenti in sospeso nella dashboard e filtro ?status=.
            models.Index(fields=["status"], name="payment_status_idx"),
            # Filtri per periodo del registro di cassa.
            models.Index(fields=["date"], name="payment_date_idx"),
        ]
        constraints = [
            # Uno storno ha sempre il collegamento, e solo lo storno lo ha.
            models.CheckConstraint(
                condition=(
                    models.Q(status="reversal", reversal_of__isnull=False)
                    | (~models.Q(status="reversal") & models.Q(reversal_of__isnull=True))
                ),
                name="payment_reversal_link_matches_status",
            ),
            # Lo storno ripete l'importo dell'originale: il segno lo dà lo stato.
            models.CheckConstraint(
                condition=~models.Q(status="reversal") | models.Q(amount__gt=0),
                name="payment_reversal_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} — {self.amount} ({self.status})"

    def tenant_keys(self) -> tuple[int, int]:
        # Chiavi usate dai permessi per oggetto: (studio, insegnante) del proprietario.
        # Vedi docs/learning/concetti/isolamento-tenant-e-bola.md e ADR-011.
        return self.student.studio_id, self.student.teacher_id

    def clean(self) -> None:
        # Stessa regola dell'API, valida anche nell'admin di Django (che chiama full_clean()).
        # Import locale: services importa i modelli, un import in cima farebbe un ciclo.
        from .services import ensure_package_matches_student

        if self.student_id is not None:
            ensure_package_matches_student(self.student, self.package)


class CheckoutSession(models.Model):
    """Un tentativo di pagamento online per un pacchetto (una Checkout Session di Stripe).

    ADR-013. Il tentativo nasce "open" e diventa completed, failed o expired: da lì in poi
    non cambia più (vedi `apply_session_state` in services.py).
    """

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        EXPIRED = "expired", "Expired"

    # UUID: finisce nella chiave di idempotenza e nei metadati di Stripe, e non è
    # indovinabile negli URL.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="checkouts")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    # Unico: è il legame col lato Stripe e serve a ritrovare il tentativo dal webhook.
    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    url = models.URLField(max_length=2000, blank=True)
    # Importo e valuta sono copiati qui al momento della creazione: se il prezzo del
    # pacchetto cambia dopo, il tentativo resta quello che il pagante ha visto.
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["package", "status"], name="checkout_package_status_idx"),
            # Riconciliazione oraria: tentativi ancora aperti oltre la scadenza. È un indice
            # parziale (solo le righe "open"): resta piccolo anche con molto storico.
            models.Index(
                fields=["expires_at"],
                name="checkout_open_expiry_idx",
                condition=models.Q(status="open"),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.package} — {self.status}"


class WebhookEvent(models.Model):
    """Una notifica di Stripe, salvata una volta sola per id evento (ADR-014).

    L'unicità di `stripe_event_id` trasforma i tentativi ripetuti e i doppioni di Stripe in
    operazioni senza effetto; `processed_at` rende idempotente il task che li elabora.
    Spiegazione completa: docs/learning/concetti/webhook-idempotenti.md.
    """

    stripe_event_id = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=100)
    payload = models.JSONField()
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    # Quante volte l'elaborazione è partita: utile per capire eventi che si bloccano.
    attempts = models.PositiveSmallIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.type} {self.stripe_event_id}"


class PaymentInstructions(models.Model):
    """Come lo studio vuole essere pagato: un solo insieme per studio (fase 8, ADR-036).

    Intestatario e IBAN sono cifrati a riposo (constitution X, ADR-030) e non compaiono mai nei
    log, nei report di errore o nel registro delle azioni. MusicStudio non muove né verifica
    denaro: i genitori pagano fuori dall'app e l'insegnante segna il pagamento come ricevuto.
    """

    studio = models.OneToOneField(
        "studios.Studio", on_delete=models.CASCADE, related_name="payment_instructions"
    )
    account_holder = EncryptedTextField(blank=True)
    iban = EncryptedTextField(blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    # Per esempio cosa scrivere nella causale del bonifico: non è un segreto, resta in chiaro.
    note = models.CharField(max_length=200, blank=True)
    # Elenco intero letto e scritto in blocco, mai interrogato: JSON basta (research R8).
    # Fino a 5 voci {"label": ..., "url": ...}; il controllo è nel serializer.
    links = models.JSONField(default=list, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        # Nessun dato bancario nella rappresentazione testuale (finirebbe nell'admin e nei log).
        return f"Payment instructions of studio #{self.studio_id}"


class Receipt(models.Model):
    """Ricevuta di pagamento non fiscale di un pagamento incassato (fase 8, ADR-035).

    Al massimo una per pagamento. Il numero è `AAAA-NNNN`, unico per studio e anno, assegnato una
    volta sola alla prima emissione e mai cambiato né riusato. Il PDF non si salva: si genera al
    momento dai dati attuali (un nome salvato sopravviverebbe a una richiesta di cancellazione).
    Spiegazione: docs/learning/concetti/ricevute-non-fiscali.md.
    """

    class Language(models.TextChoices):
        IT = "it", "Italiano"
        EN = "en", "English"

    # CASCADE solo per il job di conservazione dei pagamenti vecchi (10 anni): le ricevute
    # seguono il loro pagamento. I numeri non si riusano comunque: si prende il massimo.
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name="receipt")
    # Salvato (anche se ricavabile dallo studente) per poter dichiarare l'unicità del numero
    # per studio direttamente nel database.
    studio = models.ForeignKey("studios.Studio", on_delete=models.PROTECT, related_name="+")
    year = models.PositiveSmallIntegerField()
    sequence = models.PositiveIntegerField()
    language = models.CharField(max_length=2, choices=Language.choices)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-sequence"]
        constraints = [
            # La rete di sicurezza dietro il lock: due ricevute dello stesso studio e anno non
            # possono avere lo stesso numero, qualunque cosa faccia il codice.
            models.UniqueConstraint(
                fields=["studio", "year", "sequence"], name="unique_receipt_number_per_studio_year"
            )
        ]

    def __str__(self) -> str:
        return f"Receipt {self.number}"

    @property
    def number(self) -> str:
        return f"{self.year}-{self.sequence:04d}"
