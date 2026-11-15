"""Registrazione minima di studi e insegnanti nell'admin di Django.

FUTURO (rafforzamento dell'admin, fase 5 in CLAUDE.md): colonne e filtri, e nessuna modifica che
salti il limite di insegnanti per studio di services.py.
"""

from django.contrib import admin

from .models import Studio, Teacher

admin.site.register(Studio)
admin.site.register(Teacher)
