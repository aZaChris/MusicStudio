"""Admin di Django per i pagamenti."""

from django.contrib import admin

from .models import Payment

# Registrazione minima. FUTURO (rafforzamento dell'admin, fase 5 in CLAUDE.md): elenco con
# colonne e filtri, campi di sola lettura per i pagamenti online, nessuna cancellazione.
admin.site.register(Payment)
