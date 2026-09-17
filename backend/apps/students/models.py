from django.conf import settings
from django.db import models

from apps.studios.models import Teacher


class Student(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    instrument = models.CharField(max_length=100)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name="students")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def active_package(self):
        return self.packages.filter(lessons_remaining__gt=0).order_by("-purchase_date").first()


class ParentAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parent_account"
    )
    students = models.ManyToManyField(
        Student, through="ParentStudentLink", related_name="parent_accounts"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.email


class ParentStudentLink(models.Model):
    parent = models.ForeignKey(ParentAccount, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["parent", "student"], name="unique_parent_student_link")
        ]

    def __str__(self) -> str:
        return f"{self.parent} -> {self.student}"
