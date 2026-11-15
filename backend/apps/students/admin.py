"""Registrazione minima di studenti e genitori nell'admin di Django.

FUTURO (rafforzamento dell'admin, fase 5 in CLAUDE.md): colonne e filtri per studio, e nessuna
modifica che salti i controlli di services.py. Sono dati personali: l'accesso va tenuto stretto.
"""

from django.contrib import admin

from .models import ParentAccount, ParentStudentLink, Student

admin.site.register(Student)
admin.site.register(ParentAccount)
admin.site.register(ParentStudentLink)
