from django.contrib import admin

from .models import ParentAccount, ParentStudentLink, Student

admin.site.register(Student)
admin.site.register(ParentAccount)
admin.site.register(ParentStudentLink)
