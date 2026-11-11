from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.accounts.managers import UserManager


class User(AbstractUser):
    """Custom user: email login, a coarse org role (employee vs hr_admin)
    and a department string, used throughout the app to gate what
    KnowledgeEntry rows a request can see (apps/knowledge/views.py) and to
    identify the "requesting employee" for semantic search
    (apps/knowledge/services/search.py). There is no self-registration
    endpoint - accounts are provisioned by an hr_admin or the demo seed
    migration, since role/department assignment isn't something a user
    should be able to grant themselves."""

    class Role(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        HR_ADMIN = "hr_admin", "HR Admin"

    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True, default="")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    department = models.CharField(max_length=100, blank=True, default="")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_hr_admin(self):
        return self.role == self.Role.HR_ADMIN
