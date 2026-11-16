"""Serializer dei pagamenti: cosa entra e cosa esce dall'API."""

from decimal import Decimal
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.common.serializers import ScopedRelatedFieldsMixin
from apps.common.tenancy import get_tenant

from .models import CheckoutSession, Payment, Receipt, StudioPaymentAccount
from .selectors import is_fully_reversed, is_reversed, reversed_amount_of


class PaymentSerializer(ScopedRelatedFieldsMixin, serializers.ModelSerializer[Payment]):
    # Pagamento in lettura e scrittura. Il mixin limita i campi `student` e `package` agli
    # oggetti del proprio studio: senza, un insegnante potrebbe collegare un pagamento a uno
    # studente di un altro studio (docs/learning/concetti/isolamento-tenant-e-bola.md).
    # Commento e non docstring: i docstring dei serializer finiscono in openapi.yaml.

    student_name = serializers.CharField(source="student.full_name", read_only=True)
    # Fase 8: campi calcolati o riservati al personale (specs/008-cash-register-receipts).
    # `reversed` e `reversal_id` si ricavano dalla riga di storno già caricata dal selector.
    reversed = serializers.SerializerMethodField()
    reversal_id = serializers.SerializerMethodField()
    receipt_number = serializers.SerializerMethodField()
    # Fase 9: quanto è stato stornato (anche in parte, per i rimborsi parziali) e se c'è una
    # contestazione aperta. `cause` (sulle righe di storno) dice se è una correzione a mano, un
    # rimborso o una contestazione persa.
    reversed_amount = serializers.SerializerMethodField()
    under_dispute = serializers.SerializerMethodField()
    # Chi ha creato la riga e perché è stata stornata: li vede solo il personale dello studio.
    # required=False: per genitori e studenti adulti i due campi mancano del tutto (vedi
    # to_representation), quindi nel contratto sono opzionali.
    recorded_by = serializers.IntegerField(
        source="recorded_by_id", read_only=True, allow_null=True, required=False
    )
    reason = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Payment
        fields = [
            "id",
            "student",
            "student_name",
            "package",
            "amount",
            "date",
            "method",
            "status",
            "checkout",
            "reversal_of",
            "reversed",
            "reversal_id",
            "reversed_amount",
            "under_dispute",
            "cause",
            "receipt_number",
            "recorded_by",
            "reason",
        ]
        # `checkout` lo imposta solo il webhook: dall'API non si può forgiare un pagamento
        # "online" a mano.
        read_only_fields = ["checkout", "reversal_of", "cause"]

    def get_reversed(self, obj: Payment) -> bool:
        # Stornato per intero. Dagli elenchi arriva dall'annotazione del selector (nessuna query
        # per riga); per un oggetto appena creato `is_reversed` fa una query sola.
        return is_reversed(obj)

    def get_reversal_id(self, obj: Payment) -> int | None:
        # Il primo storno del pagamento (con più rimborsi parziali ce n'è più d'uno).
        if hasattr(obj, "first_reversal_id"):
            first: int | None = obj.first_reversal_id
            return first
        return (
            Payment.objects.filter(reversal_of=obj.pk)
            .order_by("id")
            .values_list("id", flat=True)
            .first()
        )

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_reversed_amount(self, obj: Payment) -> str:
        return f"{reversed_amount_of(obj):.2f}"

    @extend_schema_field(serializers.BooleanField())
    def get_under_dispute(self, obj: Payment) -> bool:
        annotated = getattr(obj, "under_dispute", None)
        if annotated is not None:
            return bool(annotated)
        return obj.disputes.filter(status="open").exists()

    def get_receipt_number(self, obj: Payment) -> str | None:
        # Dal select_related del selector: nessuna query. Senza ricevuta Django solleva
        # RelatedObjectDoesNotExist (un ObjectDoesNotExist).
        try:
            return obj.receipt.number
        except ObjectDoesNotExist:
            return None

    def validate_status(self, value: str) -> str:
        # Lo storno nasce solo dal service `reverse_payment`: dall'API non si forgia.
        if value == Payment.Status.REVERSAL:
            raise serializers.ValidationError(
                "A reversal can only be made with the reverse action."
            )
        return value

    def to_representation(self, instance: Payment) -> dict[str, Any]:
        data: dict[str, Any] = super().to_representation(instance)
        # Genitori e studenti adulti vedono i pagamenti ma non chi li ha registrati né il motivo
        # di uno storno (testo libero, cifrato nel database).
        ctx = get_tenant(self.context.get("request"))
        if not (ctx.is_owner or ctx.is_teacher):
            data.pop("reason", None)
            data.pop("recorded_by", None)
        return data


class ReverseRequestSerializer(serializers.Serializer[None]):
    # Corpo di POST /payments/{id}/reverse/: il motivo è obbligatorio e breve. È testo libero,
    # quindi nel database finisce cifrato (constitution X).
    reason = serializers.CharField(min_length=1, max_length=200, trim_whitespace=True)


class ReversalSerializer(PaymentSerializer):
    # Risposta di reverse: la riga di storno più `refund`, sempre false. Lo storno corregge il
    # registro, non restituisce denaro: il prodotto non muove soldi (FR-007).
    refund = serializers.SerializerMethodField()

    class Meta(PaymentSerializer.Meta):
        fields = [*PaymentSerializer.Meta.fields, "refund"]

    def get_refund(self, obj: Payment) -> bool:
        return False


class PeriodQuerySerializer(serializers.Serializer[None]):
    # Parametri ?date_from=&date_to= del registro: date locali inclusive (YYYY-MM-DD).
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class ExportQuerySerializer(serializers.Serializer[None]):
    # Per le esportazioni il periodo è obbligatorio (e al massimo di un anno, controllato dal
    # service/selector): non si esporta "tutto" per sbaglio.
    date_from = serializers.DateField()
    date_to = serializers.DateField()


class RegisterPeriodSerializer(serializers.Serializer[None]):
    to = serializers.DateField()
    # `from` è una parola riservata di Python: il campo si dichiara nel namespace della classe.
    locals()["from"] = serializers.DateField()


class RegisterTotalsSerializer(serializers.Serializer[None]):
    received = serializers.DecimalField(max_digits=12, decimal_places=2)
    reversed = serializers.DecimalField(max_digits=12, decimal_places=2)
    net = serializers.DecimalField(max_digits=12, decimal_places=2)


class RegisterMethodSerializer(RegisterTotalsSerializer):
    method = serializers.ChoiceField(choices=Payment.Method.choices)


class RegisterCountsSerializer(serializers.Serializer[None]):
    paid = serializers.IntegerField()
    pending = serializers.IntegerField()
    overdue = serializers.IntegerField()
    reversal = serializers.IntegerField()


class RegisterSummarySerializer(serializers.Serializer[dict[str, Any]]):
    # Risposta di GET /payments/register/summary/: totali del periodo, per metodo e conteggi.
    period = RegisterPeriodSerializer()
    totals = RegisterTotalsSerializer()
    by_method = RegisterMethodSerializer(many=True)
    counts = RegisterCountsSerializer()


class PaymentLinkSerializer(serializers.Serializer[dict[str, str]]):
    # Un link di pagamento esterno (PayPal, Satispay...). Forma e `https` si controllano nel
    # service: così la regola vale anche fuori dall'API.
    # `label` è anche un attributo dei campi DRF: la metaclasse lo toglie dalla classe, quindi
    # dichiararlo qui è sicuro, ma mypy non lo sa.
    label = serializers.CharField(max_length=40)  # type: ignore[assignment]
    url = serializers.CharField(max_length=500)


class PaymentInstructionsSerializer(serializers.Serializer[dict[str, Any]]):
    # Istruzioni di pagamento dello studio: lettura e sostituzione completa (PUT). Tutti i campi
    # possono essere vuoti: un corpo tutto vuoto cancella le istruzioni.
    account_holder = serializers.CharField(max_length=100, allow_blank=True, required=False)
    iban = serializers.CharField(max_length=60, allow_blank=True, required=False)
    bank_name = serializers.CharField(max_length=100, allow_blank=True, required=False)
    note = serializers.CharField(max_length=200, allow_blank=True, required=False)
    links = PaymentLinkSerializer(many=True, required=False)
    updated_at = serializers.DateTimeField(read_only=True, allow_null=True)


class OpenInstructionsSerializer(PaymentInstructionsSerializer):
    # Per il genitore: le istruzioni di uno studio con in più chi è lo studio e la frase fissa che
    # il pagamento avviene fuori da MusicStudio e non viene verificato.
    studio_id = serializers.IntegerField()
    studio_name = serializers.CharField()
    # Gli studenti di chi chiama che hanno un pacchetto aperto in questo studio.
    student_ids = serializers.ListField(child=serializers.IntegerField())
    notice = serializers.CharField()


class ReceiptRequestSerializer(serializers.Serializer[None]):
    # Corpo di POST /payments/{id}/receipt/: la lingua è scelta alla prima emissione (it o en).
    # Se manca si usa la lingua del portale di chi emette.
    language = serializers.ChoiceField(choices=Receipt.Language.choices, required=False)


class ReceiptSerializer(serializers.ModelSerializer[Receipt]):
    # Una ricevuta emessa con i dati che il portale mostra nell'elenco. Il PDF si scarica da
    # receipts/{id}/pdf/ e si genera dai dati attuali (ADR-035).
    number = serializers.CharField(read_only=True)
    cancelled = serializers.SerializerMethodField()
    student_name = serializers.CharField(source="payment.student.full_name", read_only=True)
    amount = serializers.DecimalField(
        source="payment.amount", max_digits=8, decimal_places=2, read_only=True
    )
    date = serializers.DateField(source="payment.date", read_only=True)
    method = serializers.CharField(source="payment.method", read_only=True)

    class Meta:
        model = Receipt
        fields = [
            "id",
            "payment",
            "number",
            "language",
            "issued_at",
            "cancelled",
            "student_name",
            "amount",
            "date",
            "method",
        ]
        read_only_fields = fields

    def get_cancelled(self, obj: Receipt) -> bool:
        # "Annullata" se il pagamento è stato stornato per intero. Dall'annotazione del selector
        # (nessuna query per riga); per una ricevuta appena emessa si calcola con una query.
        annotated = getattr(obj, "payment_reversed_amount", None)
        if annotated is None:
            return is_reversed(obj.payment)
        return is_fully_reversed(obj.payment.amount, Decimal(annotated))


class CheckoutSerializer(serializers.Serializer[CheckoutSession]):
    """Response of POST /packages/{id}/checkout/: where to send the payer."""

    # Risposta di POST /packages/{id}/checkout/: dove mandare chi deve pagare.
    # Il docstring resta in inglese perché entra nel contratto OpenAPI.

    checkout_id = serializers.UUIDField(source="id")
    url = serializers.URLField()
    expires_at = serializers.DateTimeField()


class AttentionItemSerializer(serializers.Serializer[dict[str, Any]]):
    # Un evento di Stripe che non combacia col registro: solo identificativo, tipo e importo.
    id = serializers.IntegerField()
    kind = serializers.CharField()
    received_at = serializers.DateTimeField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)


class PaymentAccountSerializer(serializers.Serializer[dict[str, Any]]):
    # Stato del conto di pagamento dello studio (fase 9). `not_started` = nessun conto.
    state = serializers.ChoiceField(
        choices=["not_started", *StudioPaymentAccount.State.values], read_only=True
    )
    can_accept_online = serializers.BooleanField()
    test_mode = serializers.BooleanField()
    dashboard_url = serializers.CharField(allow_null=True)
    state_changed_at = serializers.DateTimeField(allow_null=True)
    needs_attention = AttentionItemSerializer(many=True)


class OnboardingLinkSerializer(serializers.Serializer[dict[str, Any]]):
    # Risposta di POST /payment-account/onboarding/: dove mandare il titolare (pagina di Stripe).
    url = serializers.CharField()
    expires_at = serializers.DateTimeField(allow_null=True)
