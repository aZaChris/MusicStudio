"""Filtri dell'elenco dei pagamenti: stato, studente, metodo e periodo (registro di cassa)."""

import django_filters

from .models import Payment


class PaymentFilter(django_filters.FilterSet):
    # Le date sono inclusive e sono date locali (Europe/Rome), come `Payment.date`.
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Payment
        fields = ["status", "student", "method", "date_from", "date_to"]
