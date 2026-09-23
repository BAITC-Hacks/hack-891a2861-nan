from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.catalog.models import Grade, Role, Skill


class Employee(models.Model):
    employee_id = models.CharField(max_length=64, primary_key=True)
    display_name = models.CharField(max_length=128)
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="employees")
    grade = models.ForeignKey(Grade, on_delete=models.PROTECT, related_name="employees")
    tenure_months = models.PositiveIntegerField(default=0)
    organisation_unit = models.CharField(max_length=128, blank=True)
    manager_id = models.CharField(max_length=64, null=True, blank=True)
    hire_date = models.DateField(null=True, blank=True)
    work_format = models.CharField(max_length=16, blank=True)
    career_goal = models.JSONField(null=True, blank=True)
    last_review_date = models.DateField(null=True, blank=True)
    locale = models.CharField(max_length=2, default="ru")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["employee_id"]

    def __str__(self) -> str:
        return f"{self.employee_id} — {self.display_name}"


class EmployeeSkill(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="skill_levels")
    skill = models.ForeignKey(Skill, on_delete=models.PROTECT, related_name="employee_levels")
    level = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["employee", "skill"], name="unique_employee_skill"),
            models.CheckConstraint(
                condition=models.Q(level__gte=0, level__lte=5), name="employee_skill_level_0_5"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id}: {self.skill_id} = {self.level}"
