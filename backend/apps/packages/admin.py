"""Registrazione minima dei pacchetti nell'admin di Django.

FUTURO (rafforzamento dell'admin, fase 5 in CLAUDE.md): colonne, filtri per studio e saldo
in sola lettura, così da non poterlo modificare a mano saltando i service.
"""

from django.contrib import admin

from .models import Package

admin.site.register(Package)
