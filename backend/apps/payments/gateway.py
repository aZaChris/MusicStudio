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


def _reference_id(value: Any) -> str:
    # Un riferimento di Stripe è l'id oppure, se espanso, un oggetto con l'id.
    if isinstance(value, dict):
        value = value.get("id")
    return value if isinstance(value, str) else ""


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
    currency: str = ""
    # Id del pagamento di Stripe: lega rimborsi e contestazioni al pagamento (fase 9).
    payment_intent: str = ""

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
            currency=(data.get("currency") or "").lower(),
            payment_intent=_reference_id(data.get("payment_intent")),
        )


@dataclass(frozen=True)
class AccountInfo:
    """Ciò che ci serve di un conto collegato di Stripe (API v2), indipendente dall'SDK.

    Solo lo stato: la capacità di incassare con carta e *quante* informazioni Stripe chiede
    ancora. I dettagli (documenti, dati bancari, nomi) restano sulla pagina di Stripe e non
    entrano mai nell'app (constitution X).
    """

    id: str
    # Stato della capacità "card_payments" del conto: active | pending | restricted | ... (vuoto
    # se Stripe non lo riporta). È la sola cosa che decide se si può incassare.
    card_payments: str = ""
    open_requirements: int = 0
    closed: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AccountInfo":
        merchant = (data.get("configuration") or {}).get("merchant") or {}
        capability = (merchant.get("capabilities") or {}).get("card_payments") or {}
        entries = (data.get("requirements") or {}).get("entries") or []
        return cls(
            id=data["id"],
            card_payments=capability.get("status") or "",
            open_requirements=len(entries),
            closed=bool(data.get("closed")),
        )


@dataclass(frozen=True)
class AccountLink:
    """Indirizzo temporaneo della pagina di Stripe dove il titolare completa i suoi dati."""

    url: str
    expires_at: datetime.datetime | None = None


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
    stripe_account: str | None = None,
) -> SessionInfo:
    """Crea su Stripe la pagina di pagamento. Importo in centesimi, scadenza esplicita.

    Con `stripe_account` la sessione nasce sul conto collegato dello studio (pagamento diretto,
    ADR-037): i soldi arrivano a lui e non alla piattaforma. Niente `application_fee_amount`, niente
    `on_behalf_of`: la piattaforma non prende commissioni e non tocca denaro.
    """
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
            options=_options(idempotency_key=idempotency_key, stripe_account=stripe_account),
        )
    except stripe.StripeError as exc:
        raise PaymentsUnavailable("The payment provider is not reachable.") from exc
    return SessionInfo.from_dict(_as_dict(session))


def retrieve_checkout_session(session_id: str, stripe_account: str | None = None) -> SessionInfo:
    """Legge lo stato attuale di una sessione (usato dalla riconciliazione oraria).

    Una sessione creata sul conto dello studio si legge solo con quel conto nell'intestazione.
    """
    try:
        session = _client().v1.checkout.sessions.retrieve(
            session_id, options=_options(stripe_account=stripe_account)
        )
    except stripe.StripeError as exc:
        raise PaymentsUnavailable("The payment provider is not reachable.") from exc
    return SessionInfo.from_dict(_as_dict(session))


def _options(
    *, idempotency_key: str | None = None, stripe_account: str | None = None
) -> stripe.RequestOptions:
    # Opzioni di richiesta dell'SDK: la chiave di idempotenza e, per i pagamenti diretti, il
    # conto collegato su cui agire (intestazione Stripe-Account).
    options: stripe.RequestOptions = {}
    if idempotency_key:
        options["idempotency_key"] = idempotency_key
    if stripe_account:
        options["stripe_account"] = stripe_account
    return options


def create_account(*, studio_id: int, idempotency_key: str) -> AccountInfo:
    """Crea il conto collegato dello studio (API v2, dashboard completa, ADR-037).

    Lo studio è l'esercente e vede il suo Stripe; commissioni e perdite le copre Stripe (la
    sola combinazione che Stripe ammette per una piattaforma nuova). Dati personali: nessuno. Né
    email né nome: il titolare li inserisce sulla pagina di Stripe. Mandiamo solo l'id dello studio.
    """
    params: dict[str, Any] = {
        "identity": {"country": "IT"},
        "dashboard": "full",
        "configuration": {"merchant": {"capabilities": {"card_payments": {"requested": True}}}},
        "defaults": {
            "responsibilities": {"fees_collector": "stripe", "losses_collector": "stripe"}
        },
        "metadata": {"studio_id": str(studio_id)},
    }
    try:
        account = _client().v2.core.accounts.create(
            params=params,  # type: ignore[arg-type]
            options=_options(idempotency_key=idempotency_key),
        )
    except stripe.StripeError as exc:
        raise PaymentsUnavailable("The payment provider is not reachable.") from exc
    return AccountInfo.from_dict(_as_dict(account))


def create_account_link(*, account_id: str, return_url: str, refresh_url: str) -> AccountLink:
    """Indirizzo della pagina ospitata di Stripe dove il titolare completa l'attivazione.

    Dura pochi minuti e si usa una volta. Con la raccolta dei dati a carico di Stripe, i termini di
    servizio li accetta solo il titolare lì: non esiste una via API (ADR-037).
    """
    params: dict[str, Any] = {
        "account": account_id,
        "use_case": {
            "type": "account_onboarding",
            "account_onboarding": {"return_url": return_url, "refresh_url": refresh_url},
        },
    }
    try:
        link = _as_dict(
            _client().v2.core.account_links.create(params=params)  # type: ignore[arg-type]
        )
    except stripe.StripeError as exc:
        raise PaymentsUnavailable("The payment provider is not reachable.") from exc
    expires = link.get("expires_at")
    return AccountLink(
        url=link["url"],
        expires_at=datetime.datetime.fromisoformat(expires.replace("Z", "+00:00"))
        if expires
        else None,
    )


def retrieve_account(account_id: str) -> AccountInfo:
    """Legge lo stato attuale del conto collegato (capacità di incassare e requisiti aperti)."""
    try:
        account = _client().v2.core.accounts.retrieve(
            account_id,
            params={"include": ["requirements", "configuration.merchant"]},
        )
    except stripe.StripeError as exc:
        raise PaymentsUnavailable("The payment provider is not reachable.") from exc
    return AccountInfo.from_dict(_as_dict(account))


def verify_event(
    payload: bytes, signature: str | None, secret: str | None = None
) -> dict[str, Any]:
    """Controlla l'header Stripe-Signature (HMAC di timestamp + corpo grezzo) e legge l'evento.

    Deve ricevere il corpo grezzo della richiesta: un JSON ri-serializzato cambierebbe i byte
    e la firma non corrisponderebbe mai.
    """
    # Due endpoint, due segreti (ADR-039): quello del conto della piattaforma e quello dei conti
    # collegati. Chi chiama passa il suo; senza argomento vale quello della piattaforma.
    secret = settings.STRIPE_WEBHOOK_SECRET if secret is None else secret
    if not secret or not signature:
        raise InvalidWebhook("Missing webhook secret or signature.")
    try:
        stripe.Webhook.construct_event(payload, signature, secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise InvalidWebhook(str(exc)) from exc
    event: dict[str, Any] = json.loads(payload)
    return event
