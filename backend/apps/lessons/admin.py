"""Admin di Django per le lezioni."""

from django.contrib import admin

from .models import Lesson

# Registrazione minima. FUTURO (rafforzamento dell'admin, fase 5 in CLAUDE.md): colonne e
# filtri per stato e data, e nessuna modifica che salti i controlli di services.py.
admin.site.register(Lesson)
