from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        HR = "hr", "HR"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.EMPLOYEE)
    organisation_unit = models.CharField(max_length=128, blank=True)

    def __str__(self) -> str:
        return self.username
