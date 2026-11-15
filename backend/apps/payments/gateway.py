"""Gateway di Stripe: l'unico modulo che importa `stripe` (ADR-013).

Tutto il resto del codice parla con queste funzioni e con semplici classi di dati, così:
- i test sostituiscono questo modulo con un finto (niente rete, niente account);
- cambiare fornitore, o aggiornare l'SDK, tocca un solo file.

Regole seguite (buone pratiche Stripe): un'istanza `StripeClient` (mai la chiave globale),
Checkout Session in modalità `payment`, nessun `payment_method_types` (i metodi dinamici si
configurano nella Dashboard), chiavi di idempotenza in creazione, webhook con firma verificata.
Spiegazione: docs/learning/concetti/pagamenti-online-stripe.md.

FUTURO (secondo fornitore, per esempio PayPal diretto): si aggiunge un modulo gemello con le
stesse funzioni (`create_checkout_session`, `retrieve_checkout_session`, `verify_event`) e un
campo "fornitore" su CheckoutSession. Va deciso insieme a chi incassa: vedi il commento in
testa a models.py. Con Stripe, PayPal e carte si abilitano dalla Dashboard senza codice nuovo.
"""

import datetime
import json
from dataclasses import dataclass, field
from typing import Any

import stripe
from django.conf import settings

from apps.common.exceptions import ServiceUnavailable

# Etichetta che marca le nostre sessioni nella Dashboard di Stripe (testo fisso + 8 lettere
# casuali).
INTEGRATION_IDENTIFIER = "musicstudio_packages_qwhrmtzc"


class PaymentsUnavailable(ServiceUnavailable):
    """Pagamenti non configurati o Stripe non raggiungibile: l'API risponde 503."""

    code = "payments_unavailable"


class InvalidWebhook(Exception):
    """Firma mancante o non valida, oppure contenuto malformato."""


@dataclass(frozen=True)
class SessionInfo:
    """Ciò che ci serve di una Checkout Session di Stripe, indipendente dall'SDK.

    Il resto dell'app non vede mai gli oggetti di Stripe: vede questa classe.
    """

    id: str
    status: str  # open | complete | expired
    payment_status: str  # paid | unpaid | no_payment_required
    url: str = ""
    amount_total: int | None = None  # in centesimi
    expires_at: datetime.datetime | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionInfo":
        """Costruisce l'oggetto da un dizionario (risposta API o payload del webhook)."""
        expires = data.get("expires_at")
        return cls(
            id=data["id"],
            status=data.get("status") or "",
            payment_status=data.get("payment_status") or "",
            url=data.get("url") or "",
            amount_total=data.get("amount_total"),
            expires_at=datetime.datetime.fromtimestamp(expires, datetime.UTC) if expires else None,
            metadata=dict(data.get("metadata") or {}),
        )


def _client() -> stripe.StripeClient:
    # Senza chiave i pagamenti online sono semplicemente spenti, non un errore di server.
    # La chiave live è comunque bloccata all'avvio (config/settings/prod.py, ADR-013).
    if not settings.STRIPE_API_KEY:
        raise PaymentsUnavailable("Online payments are not configured.")
    return stripe.StripeClient(settings.STRIPE_API_KEY, max_network_retries=2)


def _as_dict(obj: Any) -> dict[str, Any]:
    # L'SDK restituisce un suo oggetto; lo convertiamo in dizionario semplice.
    data: dict[str, Any] = json.loads(str(obj)) if not isinstance(obj, dict) else obj
    return data


def create_checkout_session(
    *,
    checkout_id: str,
    amount_cents: int,
    currency: str,
    description: str,
    expires_at: datetime.datetime,
    idempotency_key: str,
    customer_email: str | None = None,
) -> SessionInfo:
    """Crea su Stripe la pagina di pagamento. Importo in centesimi, scadenza esplicita."""
    params: dict[str, Any] = {
        "mode": "payment",
        "line_items": [
            {
                "quantity": 1,
                "price_data": {
                    "currency": currency,
                    "unit_amount": amount_cents,
                    "product_data": {"name": description},
                },
            }
        ],
        "success_url": settings.CHECKOUT_SUCCESS_URL,
        "cancel_url": settings.CHECKOUT_CANCEL_URL,
        # Stripe ci restituisce questo id nel webhook: è così che ritroviamo il tentativo.
        "client_reference_id": checkout_id,
        "metadata": {"checkout_id": checkout_id},
        "expires_at": int(expires_at.timestamp()),
        "integration_identifier": INTEGRATION_IDENTIFIER,
    }
    if customer_email:
        params["customer_email"] = customer_email
    try:
        session = _client().v1.checkout.sessions.create(
            params=params,  # type: ignore[arg-type]
            # Stessa chiave = stessa sessione: un nuovo tentativo di rete non ne crea due.
            options={"idempotency_key": idempotency_key},
        )
    except stripe.StripeError as exc:
        raise PaymentsUnavailable("The payment provider is not reachable.") from exc
    return SessionInfo.from_dict(_as_dict(session))


def retrieve_checkout_session(session_id: str) -> SessionInfo:
    """Legge lo stato attuale di una sessione (usato dalla riconciliazione oraria)."""
    try:
        session = _client().v1.checkout.sessions.retrieve(session_id)
    except stripe.StripeError as exc:
        raise PaymentsUnavailable("The payment provider is not reachable.") from exc
    return SessionInfo.from_dict(_as_dict(session))


def verify_event(payload: bytes, signature: str | None) -> dict[str, Any]:
    """Controlla l'header Stripe-Signature (HMAC di timestamp + corpo grezzo) e legge l'evento.

    Deve ricevere il corpo grezzo della richiesta: un JSON ri-serializzato cambierebbe i byte
    e la firma non corrisponderebbe mai.
    """
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret or not signature:
        raise InvalidWebhook("Missing webhook secret or signature.")
    try:
        stripe.Webhook.construct_event(payload, signature, secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise InvalidWebhook(str(exc)) from exc
    event: dict[str, Any] = json.loads(payload)
    return event
