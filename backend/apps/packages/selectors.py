"""Read queries for packages."""

from typing import Any

from django.db.models import QuerySet

from apps.common.scoping import packages_visible_to

from .models import Package


def packages_for(user: Any) -> QuerySet[Package]:
    return packages_visible_to(user)
