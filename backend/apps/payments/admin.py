"""Admin dei pagamenti: tutto in sola lettura (ADR-041).

Pagamenti, storni, ricevute, contestazioni, checkout ed eventi di Stripe sono record definitivi:
si correggono con uno storno dai service, mai a mano (fase 8, ADR-034). Il motivo di uno storno
è cifrato e non compare nell'admin. Conto collegato e istruzioni di pagamento (IBAN cifrato) non
sono registrati: l'operatore non ne ha bisogno.
"""

from django.contrib import admin

from apps.common.admin_mixins import ReadOnlyAdmin

from .models import CheckoutSession, Payment, PaymentDispute, Receipt, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ("id", "date", "amount", "method", "status", "student", "reversal_of")
    list_filter = ("status", "method")
    exclude = ("reason",)


@admin.register(Receipt)
class ReceiptAdmin(ReadOnlyAdmin):
    list_display = ("id", "studio", "year", "sequence", "payment", "issued_at")


@admin.register(PaymentDispute)
class PaymentDisputeAdmin(ReadOnlyAdmin):
    list_display = ("id", "payment", "status", "amount", "opened_at", "closed_at")
    list_filter = ("status",)


@admin.register(CheckoutSession)
class CheckoutSessionAdmin(ReadOnlyAdmin):
    list_display = ("id", "package", "amount", "currency", "status", "created_at")
    list_filter = ("status",)


@admin.register(WebhookEvent)
class WebhookEventAdmin(ReadOnlyAdmin):
    # Il payload è già ripulito dai dati personali prima di essere salvato (ADR-039).
    list_display = ("stripe_event_id", "type", "outcome", "attempts", "received_at")
    list_filter = ("outcome", "type")
